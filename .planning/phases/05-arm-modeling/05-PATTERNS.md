# Phase 5: ARM Modeling — Pattern Map

**Mapped:** 2026-04-30
**Files analyzed:** 9 NEW + 5 MODIFIED + 13 fixture files (Phase 5 scope per CONTEXT.md D-04, D-08, D-09 + RESEARCH §"Recommended Plan Structure")
**Analogs found:** 12 / 14 (2 partial — `references/arm-mechanics.md` and `tests/fixtures/arm/oracle/*.pdf` have no exact codebase analog; both call out RESEARCH.md as the pattern source)

## File Classification

### NEW files (Phase 5 creates)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `lib/arm.py` | domain-engine (Pydantic models + per-period iteration) | transform (Loan + ARMTerms + index_path → ARMSchedule) | `lib/affordability.py` (models + composition) + `lib/amortize.py` (per-period engine) | exact (composite) |
| `scripts/arm_simulate.py` | CLI entrypoint | request-response (JSON-in stdin/file → JSON-out stdout) | `scripts/affordability.py` | exact |
| `scripts/_cli_helpers.py` | shared utility module (factor) | utility (no I/O; pure function) | NONE existing — closest naming/import-discipline analog is `lib/money.py` shared across `lib/amortize.py` + `lib/affordability.py` | weak (pattern-only, factor-extract from `scripts/affordability.py:70-123`) |
| `references/arm-mechanics.md` | reference doc | static doc | `data/reference/*.yml` schema is YAML; no `references/*.md` exists yet — this is a brand-new doc style (per RESEARCH §Q4) | weak (RESEARCH-driven; no codebase analog) |
| `tests/test_arm.py` | test (golden + structural + invariant + CLI smoke + meta) | test | `tests/test_affordability.py` (closest by surface area) + `tests/test_amortize.py` (closest by golden+invariant structure) | exact (composite) |
| `tests/fixtures/arm/*.json` (10 hand-calc fixtures) | test fixture (one-per-file JSON) | static data | `tests/fixtures/affordability/*.json` (shape) + `tests/fixtures/amortize/*.json` (structure) | exact |
| `tests/fixtures/arm/oracle/bankrate_*.pdf` + `.json` | test fixture (oracle capture pair) | static data + transcription | `tests/fixtures/golden_pmt.json` (Phase 1 oracle anchor pattern) — but PDF capture format itself is new | weak (idea analog only — capture-as-fixture is Phase 5's invention; CONTEXT.md D-04 specifies the new capture schema) |
| `tests/fixtures/arm/oracle/vertex42_5_1_capture_2026.pdf` + `.json` | test fixture (oracle cross-check pair) | static data | (same as above) | weak |
| `tests/fixtures/arm/oracle/americu_5_6_disclosure_2022.pdf` + `.json` | test fixture (lender-disclosure oracle) | static data | (same as above; lender-published frozen artifact) | weak |

### MODIFIED files (Phase 5 touches existing)

| Modified File | Role | Modification | Closest Analog Pattern |
|---|---|---|---|
| `tests/conftest.py` | test fixture loader | extend with `arm_fixture` factory | own file lines 38-70 (`amortize_fixture` + `affordability_fixture` factories) |
| `lib/money.py` (D-14 candidate) | money discipline helper | OPTIONAL: add public `quantize_rate(Decimal) -> Decimal` | own file lines 39-46 (`quantize_cents`); excerpt to copy lives at `lib/affordability.py:613-627` |
| `lib/affordability.py` (D-14) | (only if D-14 promotion path) | replace private `_quantize_rate` def with `from lib.money import quantize_rate as _quantize_rate` shim, OR rename 4 call-sites to `quantize_rate` | n/a (mechanical edit) |
| `scripts/amortize.py` (D-discretion factor) | (only if `_cli_helpers.py` is factored) | replace inline `_find_json_float_loc` def with `from scripts._cli_helpers import find_json_float_loc` | n/a (mechanical edit; original lives at `scripts/amortize.py:72-122`) |
| `scripts/affordability.py` (D-discretion factor) | (only if factored) | same mechanical replacement | n/a (original lives at `scripts/affordability.py:70-123`) |

---

## Pattern Assignments

### `lib/arm.py` (domain engine — composite analog)

**Primary analogs:**
- `lib/affordability.py` — Pydantic v2 strict+frozen+forbid models + `_validate_common` cross-field check + `_quantize_rate` helper + boundary validation discipline
- `lib/amortize.py` — `AmortizeRequest` Pydantic boundary model + `model_validator(mode="after")` cross-field validator + `_build_fixed_monthly` per-period iteration with `cumulative_interest` / `cumulative_principal` carry

**Pattern 1: Pydantic v2 strict+frozen+forbid model with model_validator** (locked-shape model)

Source: `lib/amortize.py:175-223` (`AmortizeRequest` with two `model_validator(mode="after")` cross-field checks).

```python
# lib/amortize.py:175-223
class AmortizeRequest(BaseModel):
    """Top-level request schema for scripts/amortize.py (D-19 boundary)."""

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

    @model_validator(mode="after")
    def _no_duplicate_recurring_periods(self) -> AmortizeRequest:
        seen_recurring_periods: set[int] = set()
        for entry in self.extra_principal:
            if not entry.recurring:
                continue
            if entry.period in seen_recurring_periods:
                raise ValueError(
                    f"duplicate recurring extra_principal at period {entry.period}; ..."
                )
            seen_recurring_periods.add(entry.period)
        return self
```

**Apply to `lib/arm.py`:** `ARMTerms`, `ARMRequest`, `ARMPayment`, `ARMSchedule`, `ResetEvent`, `IndexPathEntry` ALL use `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")`. The cross-field `model_validator(mode="after")` pattern above is the direct analog for `ARMRequest._index_path_periods_align_to_reset_triggers` (RESEARCH Q7 + Code Example 1 at RESEARCH lines 488-518).

**Pattern 2: Pydantic v2 model with `Field(ge=..., le=...)` constraints + `Annotated[Decimal, Field(...)]` Money/Rate types**

Source: `lib/affordability.py:441-528` (locked-shape `_CommonRequestFields` + `ForwardModeRequest` + `_validate_common` cross-field validator).

```python
# lib/affordability.py:441-510 (excerpt — 30 lines)
class _CommonRequestFields(BaseModel):
    """Shared base fields for ForwardModeRequest + ReverseModeRequest."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    household: Household
    max_dti: Rate  # caller-supplied per D-12 — no defaults
    target_loan_type: TargetLoanType
    term_months: int = Field(ge=1, le=600)
    annual_rate: Rate
    apr: Rate | None = None
    apor: Rate | None = None
    monthly_pmi: Money | None = None
    junior_liens: list[Money] = Field(default_factory=list)


def _validate_common(req: _CommonRequestFields) -> Any:
    if req.target_loan_type == "va" and req.household.va is None:
        raise ValueError("household.va block is required ...")
    if (req.apr is None) != (req.apor is None):
        raise ValueError("apr and apor must both be supplied or both be omitted ...")
    return req


class ForwardModeRequest(_CommonRequestFields):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    mode: Literal["forward"] = "forward"
    loan_amount: Money
    property_value: Money

    @model_validator(mode="after")
    def _validate_forward(self) -> ForwardModeRequest:
        _validate_common(self)
        return self
```

**Apply to `lib/arm.py`:** `ARMTerms` field shape (CONTEXT.md D-06) maps onto this — `initial_period_months: int = Field(ge=1, le=600)`, `initial_cap_bps: int = Field(ge=0, le=2000)`, `floor_rate: Rate` (REQUIRED, no default per D-02), `note_rate: Rate | None = None`. `ARMRequest` model_validator follows the `_validate_forward` shape — call helper-then-return-self.

**Pattern 3: `_quantize_rate` helper (D-14 candidate for promotion)**

Source: `lib/affordability.py:613-627` (full helper definition; ≤15 lines).

```python
# lib/affordability.py:613-627
_RATE_QUANTUM: Final[Decimal] = Decimal("0.000001")


def _quantize_rate(rate: Decimal) -> Decimal:
    """Quantize a fractional rate to 6 decimal places (lib.models.Rate constraint).

    Round-trip closure (D-09; SC-2) exposes that ltv = max_loan_amount /
    derived_property_value can produce 28-digit Decimals; the response Rate
    field rejects more than 7 total digits. Apply ROUND_HALF_UP via
    lib.money.MONEY_CONTEXT (CLAUDE.md money discipline; Phase 1 PITFALLS:
    US consumer finance uses ROUND_HALF_UP, never Python's default
    ROUND_HALF_EVEN banker's rounding).
    """
    with localcontext(MONEY_CONTEXT):
        return rate.quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP)
```

**Apply path A (D-14 promotion — recommended):** Plan 05-01 lifts these 15 lines verbatim into `lib/money.py` (rename `_quantize_rate` → `quantize_rate`, lift `_RATE_QUANTUM` constant). Update `lib/affordability.py` to import. `lib/arm.py` imports `from lib.money import quantize_cents, quantize_rate`.

**Apply path B (no promotion):** `lib/arm.py` imports `from lib.affordability import _quantize_rate as quantize_rate`. Smaller blast radius. CONTEXT.md D-14 + RESEARCH Q9 prefer Path A; planner picks.

**Pattern 4: Per-period iteration with cumulative-totals slice-stitch (the slice + stitch operation Phase 5 must augment with prior-epoch carries)**

Source: `lib/amortize.py:295-383` (`_build_fixed_monthly` — per-period loop with `cum_int`, `cum_prin`, D-09 final-period cleanup, D-10 detection rule, Schedule construction). 30 lines maximum — quoting lines 295-345 (the loop core; balance/interest/principal/extra/cumulative computation + D-09 cleanup):

```python
# lib/amortize.py:295-345 (excerpt — 50 lines, the core iteration; Phase 5 mirrors with prior-epoch carry)
def _build_fixed_monthly(
    loan: Loan,
    origination: date,
    extra_principal: Sequence[ExtraPrincipalEntry],
) -> Schedule:
    period_rate = loan.annual_rate / Decimal("12")  # D-04
    level_pmt = quantize_cents(-npf.pmt(period_rate, loan.term_months, loan.principal))

    balance = loan.principal
    cum_int = Decimal("0.00")
    cum_prin = Decimal("0.00")
    payments: list[Payment] = []

    for period in range(1, loan.term_months + 1):
        interest = quantize_cents(period_rate * balance)
        is_last_term_period = period == loan.term_months
        formulaic_principal = quantize_cents(level_pmt - interest)
        formulaic_overshoot = balance + interest <= level_pmt

        if is_last_term_period or formulaic_overshoot:
            principal_paid = balance
            payment_amount = quantize_cents(principal_paid + interest)
        else:
            principal_paid = formulaic_principal
            payment_amount = level_pmt

        remaining_after_regular = balance - principal_paid
        extra = _resolve_extra(period, extra_principal, cap=remaining_after_regular)
        balance_after = remaining_after_regular - extra

        # D-09 final-period cleanup
        if is_last_term_period and balance_after != Decimal("0.00"):
            principal_paid = principal_paid + balance_after
            payment_amount = quantize_cents(principal_paid + interest + extra)
            balance_after = Decimal("0.00")

        cum_int = quantize_cents(cum_int + interest)
        cum_prin = quantize_cents(cum_prin + principal_paid)

        payments.append(Payment(
            period=period,
            payment_date=origination + relativedelta(months=period),
            payment=payment_amount, principal=principal_paid, interest=interest,
            extra_principal=extra, balance=balance_after,
            cumulative_interest=cum_int, cumulative_principal=cum_prin,
        ))
        balance = balance_after
```

**Apply to `lib/arm.py::build_arm_schedule`:** Phase 5 does NOT reimplement this loop (per ARM-05 + CONTEXT.md D-05). Phase 5 RE-ENTERS this function once per epoch via `build_schedule(...)`, then **slices** rows `[0:reset_period_months]` (or the full tail for the FINAL epoch), and **augments cumulative_interest / cumulative_principal with prior-epoch carries** before constructing each `ARMPayment`. RESEARCH Code Example 2 (RESEARCH lines 520-632) pre-shows the slice-stitch shape with `cum_int_carry` / `cum_prin_carry` semantics. The D-09 cleanup applies ONLY to the final epoch's final row (CONTEXT.md D-03 + D-05). Phase 3 D-15 invariant (`Schedule.total_interest == payments[-1].cumulative_interest`) carries through unchanged for `ARMSchedule`.

**Pattern 5: Imports block convention**

Source: `lib/affordability.py:174-187`.

```python
# lib/affordability.py:174-187
from __future__ import annotations

import warnings
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

import numpy_financial as npf
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.amortize import build_schedule
from lib.models import Loan, Money, Rate
from lib.money import MONEY_CONTEXT, quantize_cents
```

**Apply to `lib/arm.py`:** Same import order convention. Add `from lib.models import Payment, Schedule` (since `ARMPayment(Payment)` and `ARMSchedule` parallel-not-subclass uses both). Add `from dateutil.relativedelta import relativedelta` if planner picks per-epoch origination_date offsets.

---

### `scripts/arm_simulate.py` (CLI — exact analog)

**Analog:** `scripts/affordability.py` (320 lines). Mirror exactly per CONTEXT.md D-07.

**Pattern 1: argparse + lazy-import + sys.path injection**

Source: `scripts/affordability.py:126-216` (full main() up to lazy-import block; ≤30 lines key portion).

```python
# scripts/affordability.py:126-216 (key 30 lines)
def main() -> int:
    parser = argparse.ArgumentParser(
        prog="affordability",
        description="Compute household affordability ...",
        epilog=("Input JSON shape (D-14 discriminator field 'mode'): ..."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to JSON file containing the affordability request.",
    )
    args = parser.parse_args()

    # When invoked as `python scripts/affordability.py ...`, Python puts `scripts/`
    # on sys.path, NOT the project root, so `from lib.affordability import ...`
    # fails with ModuleNotFoundError. Insert the project root.
    _project_root = str(Path(__file__).resolve().parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    # Lazy-import per D-18 / D-13: heavy deps are NOT loaded on the --help fast path.
    from lib.affordability import (
        AffordabilityRequest,
        evaluate,
    )
    from pydantic import TypeAdapter, ValidationError
```

**Apply to `scripts/arm_simulate.py`:** Same pattern. `prog="arm_simulate"`, `description="Build ARM amortization schedule ..."`, lazy-import `from lib.arm import ARMRequest, build_arm_schedule`. The sys.path injection block is **load-bearing** — keep it verbatim.

**Pattern 2: 6-key Pydantic envelope construction + JSON-float pre-validation gate**

Source: `scripts/affordability.py:236-274` (full envelope construction; ≤30 lines).

```python
# scripts/affordability.py:236-274
# D-19 + WR-02: pre-validation gate — reject JSON-numbers-with-decimal-points
# in money fields BEFORE handing to Pydantic.
float_hit = _find_json_float_loc(raw)
if float_hit is not None:
    float_loc, float_input = float_hit

    # Lazy-imported pydantic.VERSION here (NOT at module top) to preserve
    # D-18 fast --help. The version segment in the docs URL floats with
    # the runtime Pydantic version.
    from pydantic import VERSION as _pydantic_version

    _major_minor = ".".join(_pydantic_version.split(".")[:2])
    envelope = [
        {
            "type": "decimal_type",
            "loc": float_loc,
            "msg": (
                "Input should be a valid decimal — JSON string required "
                "for money/rate fields per D-19 (JSON floats are rejected "
                "at the boundary)"
            ),
            "input": float_input,
            "url": f"https://errors.pydantic.dev/{_major_minor}/v/decimal_type",
            "ctx": {
                "class": "Decimal",
                "field_path": ".".join(str(p) for p in float_loc),
            },
        }
    ]
    print(json.dumps(envelope), file=sys.stderr)
    return 2
```

**Apply to `scripts/arm_simulate.py`:** Lift verbatim. Phase 5's float-gate covers `loan.principal`, `assumed_index_rate`, `index_path[].value`, `floor_rate` per CONTEXT.md D-07. The same code handles all four — no per-field branching needed (the helper walks the entire JSON tree).

**Pattern 3: ValidationError pass-through + happy-path serialize**

Source: `scripts/affordability.py:280-316`.

```python
# scripts/affordability.py:280-316 (excerpt)
try:
    adapter: TypeAdapter[Any] = TypeAdapter(AffordabilityRequest)
    request = adapter.validate_json(raw)
except ValidationError as e:
    print(e.json(), file=sys.stderr)
    return 2

try:
    response = evaluate(request)
except MissingCountyDataError as e:
    # ... synthesize 6-key envelope manually for non-Pydantic exception classes ...
    print(json.dumps(envelope), file=sys.stderr)
    return 2

print(response.model_dump_json(indent=2))
return 0
```

**Apply to `scripts/arm_simulate.py`:** Same. Phase 5 has NO domain-specific exception classes (no `MissingCountyDataError` analog) — only Pydantic ValidationError surfaces. So:

```python
try:
    request = ARMRequest.model_validate_json(raw)
except ValidationError as e:
    print(e.json(), file=sys.stderr)
    return 2

schedule = build_arm_schedule(request)
print(schedule.model_dump_json(indent=2))
return 0
```

(Note: `scripts/amortize.py:220-225` uses `model_validate_json` direct call rather than `TypeAdapter` — Phase 5 follows `scripts/amortize.py` since `ARMRequest` is a single BaseModel, not a discriminated union.)

---

### `scripts/_cli_helpers.py` (factor — Claude's discretion D-discretion; recommended per RESEARCH §"Recommended Plan Structure")

**Analog:** NONE — Phase 5 creates this. Pattern is "shared module imported by scripts/*". The closest naming/import-discipline analog is `lib/money.py` shared across `lib/amortize.py` + `lib/affordability.py`.

**Source to factor (lift verbatim from `scripts/affordability.py:70-123`; identical helper also at `scripts/amortize.py:72-122`):**

```python
# scripts/affordability.py:70-123 (FULL helper definition — 54 lines)
def _find_json_float_loc(raw: str) -> tuple[list[str | int], str] | None:
    """Walk parsed JSON and return (loc-path, decimal-string) of the first JSON float.

    Pydantic v2 strict mode accepts JSON numbers for Decimal fields by design
    (https://docs.pydantic.dev/2.13/concepts/json/#json-parsing) — JSON has no
    distinct decimal type, so Pydantic permissively coerces JSON numbers. But
    the project's money-discipline contract (CLAUDE.md FND-01) and D-19 require
    money/rate fields be JSON STRINGS (e.g. "400000.00"). So we pre-parse with
    `parse_float=Decimal` to mark JSON-numbers-with-decimal-points as Decimal
    instances, then walk the parsed tree to find the first Decimal — its
    loc-path identifies the offending field.
    """
    from decimal import Decimal as _Decimal  # local-import: keeps --help fast (D-18)

    try:
        parsed = json.loads(raw, parse_float=_Decimal)
    except json.JSONDecodeError:
        return None

    def _walk(node: Any, path: list[str | int]) -> tuple[list[str | int], str] | None:
        if isinstance(node, _Decimal):
            return (path, str(node))
        if isinstance(node, dict):
            for k, v in node.items():
                hit = _walk(v, [*path, k])
                if hit is not None:
                    return hit
        elif isinstance(node, list):
            for i, v in enumerate(node):
                hit = _walk(v, [*path, i])
                if hit is not None:
                    return hit
        return None

    return _walk(parsed, [])
```

**Apply to `scripts/_cli_helpers.py`:** Lift verbatim. Rename `_find_json_float_loc` → `find_json_float_loc` (public; loses the leading underscore). Optionally add a sibling `make_decimal_type_envelope(loc, input_str)` helper that constructs the 6-key envelope (lifted from `scripts/affordability.py:236-273`) so `scripts/amortize.py` + `scripts/affordability.py` + `scripts/arm_simulate.py` all share both the gate AND the envelope construction. RESEARCH §"Recommended Plan Structure" Wave 4 line 476 + 480 plan-checker note insists Wave 4 verify Phase 3 + Phase 4 test suites pass unchanged after the factor.

**Weak-analog adapter:** `scripts/_cli_helpers.py` has no `__init__.py` sibling (project convention: scripts/ is intentionally not a Python package — see `tests/test_amortize.py:766-768` comment). Phase 5 must NOT add an `__init__.py`; the import works via `sys.path.insert(0, project_root)` placed in each consuming script. Verify import order: `_cli_helpers` import lives AFTER the sys.path insertion block.

---

### `references/arm-mechanics.md` (reference doc — weak analog)

**Analog:** NONE existing. No `references/*.md` files exist in the codebase (verified: `ls references/` returns "No such file or directory"). The closest convention-analog is `data/reference/*.yml` (regulatory parameter files with `source:` URL + `effective:` date) — but that is YAML, not Markdown.

**Pattern source:** RESEARCH Q4 + CONTEXT.md D-08 [REVISED 2026-04-30] specify the 6 sections + corrected citations:

1. Reset month convention (cite Fannie B2-1.4-02 — 2025-12-10 + Freddie 6302.7(b))
2. Cap precedence (cite same)
3. Floor algebra (cite same)
4. Quantization (cite Phase 4 D-09 / promoted `lib.money.quantize_rate`)
5. Negative amortization OUT of scope (cite CONTEXT.md D-12)
6. `index_series_id` semantics (Phase 12 forward-looking)
7. Teaser-ARM lifetime cap base (CFPB §1951 + engine choice — RESEARCH LM-3)

**Apply to plan:** Plan 05-05 (per RESEARCH §"Recommended Plan Structure" Wave 5) uses RESEARCH §"Per-Question Findings Q4" verbatim citation strings — the corrected URLs are pre-validated:
- https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms (last updated 2025-12-10)
- https://guide.freddiemac.com/ (§6302.7(b))
- https://sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms
- https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/

The ARMTerms model docstring (`lib/arm.py`) cites this file inline per ARM-09 / ROADMAP SC-5: `"""See references/arm-mechanics.md for reset/cap/floor convention. ..."""`.

---

### `tests/test_arm.py` (test — composite analog)

**Primary analogs:**
- `tests/test_affordability.py` (1653 lines) — fixture-loader pattern, 6-key envelope test, citation-coverage meta-test, lazy-import test, subprocess-invocation pattern
- `tests/test_amortize.py` (1067 lines) — golden + structural + invariant + CLI smoke + envelope-uniformity structure

**Pattern 1: Module header + SCRIPT_PATH constant (subprocess-invocation pattern)**

Source: `tests/test_affordability.py:9-79` (top imports + SCRIPT_PATH).

```python
# tests/test_affordability.py:9-79 (excerpt — 30 lines)
"""Phase 4 Affordability — full test surface (AFFD-01..09 + cross-cutting).

Per Phase 3 D-17 portability: subprocess invocation only, never
`import scripts.affordability` directly. SCRIPT_PATH is the single
constant edited at Phase 10 when scripts/ relocates to
.claude/skills/mortgage-ops/scripts/.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from lib.affordability import (
    AffordabilityRequest,
    AffordabilityResponse,
    # ...
    evaluate,
)
from pydantic import TypeAdapter, ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "affordability.py"
"""Phase 4 CLI lives at project-root scripts/. Phase 10 will relocate to
.claude/skills/mortgage-ops/scripts/; only this constant updates."""
```

**Apply to `tests/test_arm.py`:** Identical shape. `SCRIPT_PATH = ... / "scripts" / "arm_simulate.py"`. Add `ARM_MODULE_PATH = ... / "lib" / "arm.py"` if planner needs it (mirrors `AFFORDABILITY_MODULE_PATH:70-72`).

**Pattern 2: Subprocess CLI smoke test**

Source: `tests/test_affordability.py:685-714` (`test_AFFD_08_cli_smoke`) — also `tests/test_amortize.py:722-751` (`test_cli_smoke_subprocess_round_trip`).

```python
# tests/test_affordability.py:685-714 (excerpt — 30 lines)
def test_AFFD_08_cli_smoke(
    affordability_fixture: Callable[[str], dict[str, Any]],
    tmp_path: Path,
) -> None:
    """AFFD-08: scripts/affordability.py JSON-in/JSON-out subprocess smoke (D-13).

    Round-trip: write the conventional-80-LTV fixture's request to disk,
    invoke the CLI via subprocess, parse stdout JSON, assert it matches
    the fixture's expected_response on dollar-anchored fields.
    """
    fx = affordability_fixture("forward_conventional_80_ltv")
    request_path = tmp_path / "input.json"
    request_path.write_text(json.dumps(fx["request"]))
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(request_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    expected = fx["expected_response"]
    # Dollar anchors (D-18 exact equality)
    assert out["monthly_pi"] == expected["monthly_pi"]
    assert out["ltv"] == expected["ltv"]
    assert out["piti"] == expected["piti"]
    assert out["blocked"] == expected["blocked"]
    assert out["blocked_by"] == expected["blocked_by"]
    assert out["loan_type"] == expected["loan_type"]
```

**Apply to `tests/test_arm.py`:** `test_cli_smoke_subprocess_round_trip` (ARM-08). Use `arm_fixture("arm_5_1_payment_jump_at_61")`. Assertions: `out["payments"][59]["rate_in_effect"] == fx["expected"]["payments"][59]["rate_in_effect"]`, `out["payments"][60]["payment"] == fx["expected"]["new_pmt"]`, `out["reset_events"][0]["period"] == 61`.

**Pattern 3: Lazy-import test (D-18 fast `--help`)**

Source: `tests/test_affordability.py:1194-1242` (full test; ≤30 line excerpt of the harness body):

```python
# tests/test_affordability.py:1194-1242 (excerpt — 30 lines, the inline harness)
def test_cli_help_does_not_import_lib_affordability() -> None:
    """D-18 (Phase 3 03-04 idiom): --help must not trigger lib.affordability
    or numpy_financial import."""
    project_root = Path(__file__).resolve().parent.parent
    inline = (
        "import importlib.util, sys, json\n"
        f"sys.path.insert(0, {str(project_root)!r})\n"
        f"SCRIPT = {str(SCRIPT_PATH)!r}\n"
        "spec = importlib.util.spec_from_file_location('scripts_affordability', SCRIPT)\n"
        "assert spec is not None and spec.loader is not None\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "saved_argv = sys.argv\n"
        "sys.argv = [SCRIPT, '--help']\n"
        "exit_code = None\n"
        "try:\n"
        "    try:\n"
        "        module.main()\n"
        "    except SystemExit as exc:\n"
        "        exit_code = exc.code\n"
        "finally:\n"
        "    sys.argv = saved_argv\n"
        "result = {\n"
        "    'help_exit_code': exit_code,\n"
        "    'lib_affordability_imported': 'lib.affordability' in sys.modules,\n"
        "    'numpy_financial_imported': 'numpy_financial' in sys.modules,\n"
        "}\n"
        "print(json.dumps(result))\n"
    )
    completed = subprocess.run([sys.executable, "-c", inline], ...)
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["help_exit_code"] == 0
    assert payload["lib_affordability_imported"] is False
    assert payload["numpy_financial_imported"] is False
```

**Apply to `tests/test_arm.py`:** `test_cli_help_does_not_import_lib_arm`. Replace `'scripts_affordability'` → `'scripts_arm_simulate'` and `'lib.affordability' in sys.modules` → `'lib.arm' in sys.modules`. Also assert `'lib.amortize' in sys.modules` is False (since `lib.arm` transitively imports `lib.amortize.build_schedule` — must stay lazy).

**Pattern 4: Float-gate envelope assertion (6-key uniformity)**

Source: `tests/test_affordability.py:1245-1279` (`test_cli_rejects_float_in_loan_amount` — full test ≤30 lines).

```python
# tests/test_affordability.py:1245-1279 (excerpt — 30 lines)
def test_cli_rejects_float_in_loan_amount(tmp_path: Path) -> None:
    """D-19 + WR-02 inheritance: pre-validation gate emits 6-key envelope."""
    bad = tmp_path / "float.json"
    bad.write_text(
        '{"mode": "forward", "household": {...}, '
        '"max_dti":"0.43","target_loan_type":"conventional","term_months":360,'
        '"annual_rate":"0.065","loan_amount": 400000.00,'        # <-- JSON float, not string
        '"property_value":"500000.00"}'
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    errors = json.loads(result.stderr)
    err = errors[0]
    assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}
    assert err["type"] == "decimal_type"
    assert err["loc"] == ["loan_amount"]
    assert err["url"].startswith("https://errors.pydantic.dev/")
    assert err["url"].endswith("/v/decimal_type")
    assert err["ctx"].get("class") == "Decimal"
```

**Apply to `tests/test_arm.py`:** Five tests (one per ARM money/rate field per RESEARCH §"Phase Requirements → Test Map" lines 410-414):
- `test_cli_rejects_float_principal` (`loc == ["loan", "principal"]`)
- `test_cli_rejects_float_assumed_index_rate` (`loc == ["assumed_index_rate"]`)
- `test_cli_rejects_float_index_path_value` (`loc == ["index_path", 0, "value"]` — exercises deep loc through a list)
- `test_cli_rejects_float_floor_rate` (`loc == ["arm_terms", "floor_rate"]`)
- `test_cli_error_envelope_uniformity` — float-gate vs Pydantic ValidationError emit identical 6-key shape (analog: `tests/test_amortize.py:996-` `test_cli_error_envelope_uniformity`)

**Pattern 5: Citation-coverage meta-test (D-10 — `applied_cap` Literal coverage)**

Source: `tests/test_affordability.py:1154-1191` (`test_blocked_by_citation_coverage` — full meta-test ≤30 lines).

```python
# tests/test_affordability.py:1154-1191 (excerpt — 30 lines)
def test_blocked_by_citation_coverage() -> None:
    """RUL-12/13 inheritance: every BLOCKED_BY_* template introduced in
    lib/affordability.py is exercised by at least one fixture."""
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "affordability"
    all_blocked_by: list[str | None] = []
    for fp in sorted(fixtures_dir.glob("*.json")):
        data = json.loads(fp.read_text())
        if data.get("expected_response") is not None:
            all_blocked_by.append(data["expected_response"].get("blocked_by"))

    # DTI-CAP-* must be exercised (forward_fha_above_dti_cap)
    dti_prefix = BLOCKED_BY_DTI_CAP_TEMPLATE.split("{")[0]  # "DTI-CAP-"
    assert any(bb is not None and bb.startswith(dti_prefix) for bb in all_blocked_by), (
        "No fixture exercises DTI-CAP-{LOAN_TYPE} citation template"
    )
    # FHFA-LIMIT-* (loan-type-classify mismatch)
    assert any(bb is not None and bb.startswith("FHFA-LIMIT-") for bb in all_blocked_by), (
        "No fixture exercises FHFA-LIMIT-* citation"
    )
    # VA-residual regex
    va_pattern = re.compile(BLOCKED_BY_VA_RESIDUAL_PATTERN)
    assert any(bb is not None and va_pattern.match(bb) for bb in all_blocked_by), (
        "No fixture exercises VA-RESIDUAL-{REGION}-FAMILY-{N} citation pattern"
    )
```

**Apply to `tests/test_arm.py`:** `test_applied_cap_citation_coverage`. Per CONTEXT.md D-10 + RESEARCH §"applied_cap Literal Coverage", every Literal value (`"initial"`, `"periodic"`, `"lifetime"`, `"floor"`, `"none"`) MUST appear in at least one fixture's `expected.reset_events[i].applied_cap`. Iteration shape:

```python
fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "arm"
seen_applied_caps: set[str] = set()
for fp in sorted(fixtures_dir.glob("*.json")):
    data = json.loads(fp.read_text())
    for re_event in data.get("expected", {}).get("reset_events", []):
        seen_applied_caps.add(re_event["applied_cap"])
required = {"initial", "periodic", "lifetime", "floor", "none"}
assert required <= seen_applied_caps, f"Missing coverage: {required - seen_applied_caps}"
```

**Pattern 6: Phase 1 oracle anchor reuse (epoch 0 must match $400k @ 6.5%/30yr → $2528.27)**

Source: `tests/fixtures/golden_pmt.json:24-32` (the `computed_400k_30yr` fixture):

```json
{
  "id": "computed_400k_30yr",
  "source": "computed in-tree with Decimal + ROUND_HALF_UP; cross-verified against any standard amortization calculator",
  "principal": "400000.00",
  "annual_rate": "0.065000",
  "term_months": 360,
  "expected_monthly_pi": "2528.27",
  "rounding": "ROUND_HALF_UP",
  "notes": "Stress-test scale of Wikipedia oracle (2x principal, same rate/term)."
}
```

**Apply to `tests/test_arm.py`:** `test_initial_fixed_period_matches_phase1_oracle` (RESEARCH §Phase Requirements → Test Map line 403; LM-6 nuance). Use `golden_fixture("computed_400k_30yr")` from existing conftest fixture; build an ARMRequest with `loan = Loan(principal=400000.00, annual_rate=0.065, term_months=360)` + 5/1 ARMTerms; assert `arm_schedule.payments[0].payment == Decimal("2528.27")` AND `arm_schedule.payments[59].payment == Decimal("2528.27")` (last month of fixed period; rate hasn't changed yet).

---

### `tests/fixtures/arm/*.json` (10 hand-calc fixtures per CONTEXT.md D-09)

**Analog (shape):** `tests/fixtures/affordability/forward_conventional_80_ltv.json` — single-fixture-per-file with `request` + `expected_response` blocks + `notes`/`source` documentation.

**Analog (structure):** `tests/fixtures/amortize/biweekly_true_200k_6_5.json` — schedule-output fixture with `expected.payments[i].{period, balance, principal, interest}` rows.

**Apply:** Each fixture file: `{request: {loan, arm_terms, assumed_index_rate, index_path}, expected: {payments: [{period, rate_in_effect, payment, balance, ...}], reset_events: [{period, old_rate, new_rate, applied_cap, ...}], total_interest, final_payment_adjusted}, source: "<URL or 'computed in-tree per Selling Guide §B2-1.4-02'>"}`. CONTEXT.md §D-09 enumerates all 10 file names verbatim.

---

### `tests/fixtures/arm/oracle/*.pdf + .json` (capture-as-fixture — weak analog)

**Analog:** `tests/fixtures/golden_pmt.json` is the closest "external oracle pinned in fixture" idea (Wikipedia, CFPB worked examples) — but as a single shared JSON, not per-product capture pairs.

**Weak analog — adapt by:** CONTEXT.md D-04 [REVISED 2026-04-30] specifies the new capture pair convention:
- `<source>_<product>_capture_2026.pdf` (committed PDF artifact — browser-print or screenshot)
- `<source>_<product>_capture_2026.json` (JSON transcription of the PDF's per-period table)

The five capture pairs (per CONTEXT.md D-04):
1. `bankrate_5_1_capture_2026.pdf+.json` (primary 5/1 oracle)
2. `bankrate_7_1_capture_2026.pdf+.json` (7/1)
3. `bankrate_10_1_capture_2026.pdf+.json` (10/1)
4. `vertex42_5_1_capture_2026.pdf+.json` (Vertex42 cross-check, same scenario as Bankrate 5/1)
5. `americu_5_6_disclosure_2022.pdf + americu_5_6_disclosure.json` (lender disclosure — frozen 2022 artifact, no annual re-capture)

JSON transcription schema (planner finalizes — RESEARCH §Q3 + CONTEXT.md D-04 do NOT pin the schema): minimum fields per row are `{period, rate_in_effect, payment}`. Add `principal`, `interest`, `balance` if Bankrate/Vertex42 print them; AmericU disclosure pins the worked examples at months 61, 67, 73 only.

---

### `tests/conftest.py` (extend with `arm_fixture` loader)

**Analog:** `tests/conftest.py:38-70` (existing `amortize_fixture` + `affordability_fixture` factories) — own file lines.

**Source (ENTIRE existing factory pattern; ≤30 lines):**

```python
# tests/conftest.py:38-70 (full pattern — 33 lines)
@pytest.fixture
def amortize_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single amortize fixture by filename stem
    from tests/fixtures/amortize/. Raises FileNotFoundError if the stem doesn't exist.

    Phase 3 fixtures are one-fixture-per-file (richer schemas than the wrapped
    array shape used by golden_pmt.json) so diffs stay readable. Loader takes a
    filename stem like "biweekly_true_200k_6_5", not a fixture id within an array.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "amortize" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load


@pytest.fixture
def affordability_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single affordability fixture by filename
    stem from tests/fixtures/affordability/. Mirrors `amortize_fixture` —
    one-fixture-per-file shape; loader takes a filename stem like
    "forward_va_residual_fail", not an id within an array.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "affordability" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load
```

**Apply to `tests/conftest.py`:** Append `arm_fixture` factory mirroring this exactly:

```python
@pytest.fixture
def arm_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single ARM fixture by filename stem
    from tests/fixtures/arm/. Mirrors `amortize_fixture` and `affordability_fixture`.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "arm" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load
```

(Optional sibling: `arm_oracle_fixture` if the planner wants a separate loader for `tests/fixtures/arm/oracle/*.json` capture pairs. Recommend single `arm_fixture` with subdirectory access — caller passes `"oracle/bankrate_5_1_capture_2026"` as the stem.)

---

## Shared Patterns

### Strict + frozen + forbid Pydantic v2 model_config

**Source:** Every Phase 1+3+4 BaseModel — canonical instance at `lib/models.py:39, 51, 67` and `lib/affordability.py:346, 362, 371, 387, 401, 417, 445, 502, 520, 565`.

```python
model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
```

**Apply to:** ALL six new Phase 5 Pydantic models (`ARMTerms`, `IndexPathEntry`, `ARMRequest`, `ARMPayment`, `ResetEvent`, `ARMSchedule`). RESEARCH LM-4 explicitly notes Pydantic v2 model_config does NOT inherit through subclassing — `ARMPayment(Payment)` MUST re-specify the model_config locally.

### End-of-period quantization discipline

**Source:** `lib/money.py:39-46` (`quantize_cents`); `lib/affordability.py:613-627` (`_quantize_rate`); `lib/amortize.py:307` (call site `quantize_cents(period_rate * balance)`).

```python
# Money: 2-place ROUND_HALF_UP via quantize_cents (lib/money.py)
# Rate:  6-place ROUND_HALF_UP via _quantize_rate (lib/affordability.py — D-14 promotion candidate)
# Both use localcontext(MONEY_CONTEXT) — never mutate global Decimal context (Pitfall 9)
# Call ONCE at end-of-period; never mid-calculation
```

**Apply to:** `lib/arm.py::build_arm_schedule` — every rate output (D-02 reset formula's `fully_indexed`, `effective_floor`, `periodic_ceiling`, `lifetime_ceiling`, `new_rate`) flows through `quantize_rate(...)`. Every money output (per-row payment/principal/interest/extra/balance) flows through `quantize_cents(...)`. Phase 3 D-15 invariant (`Schedule.total_interest == payments[-1].cumulative_interest`) carries through unchanged because `ARMSchedule` mirrors Phase 1 `Schedule` shape (CONTEXT.md D-03).

### Decimal from strings, no float mixing

**Source:** `CLAUDE.md` (project-level non-negotiable); enforced by `lib/models.py` `Annotated[Decimal, Field(strict=True, ...)]` types.

```python
# Correct
Decimal("0.065")            # construct from string
Decimal(some_int) / Decimal("12")  # divide Decimal by Decimal

# Wrong
Decimal(0.065)              # float in constructor
some_decimal / 12           # int operand silently coerces (in some envs)
```

**Apply to:** Every Decimal in `lib/arm.py` and every fixture in `tests/fixtures/arm/*.json` (all money/rate fields are quoted JSON strings, never JSON numbers). The float-gate in `scripts/arm_simulate.py` enforces this at the boundary.

### 6-key Pydantic envelope on stderr (Phase 3 WR-02 closure)

**Source:** `scripts/affordability.py:236-274` (manual envelope construction for non-Pydantic surfaces); `scripts/affordability.py:283-285` (pass-through for Pydantic ValidationError via `e.json()`).

**Shape:** `[{"type", "loc", "msg", "input", "url", "ctx"}]` — list of one dict per error. URL pattern: `https://errors.pydantic.dev/{MAJOR.MINOR}/v/{error_type}` with version computed at runtime via `pydantic.VERSION` lazy-import.

**Apply to:** `scripts/arm_simulate.py` — same envelope on every ValidationError-class boundary failure (float-gate hits + Pydantic validate_json). Test `test_cli_error_envelope_uniformity` asserts identical 6-key shape across both surfaces (analog: `tests/test_amortize.py:996+`).

### Subprocess invocation in CLI tests (Phase 3 D-17 portability)

**Source:** `tests/test_amortize.py:51-52` SCRIPT_PATH constant; `tests/test_affordability.py:73-75` SCRIPT_PATH constant.

```python
SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "<name>.py"
"""Phase N CLI lives at project-root scripts/. Phase 10 will relocate to
.claude/skills/mortgage-ops/scripts/; only this constant updates."""
```

**Apply to:** `tests/test_arm.py` — `SCRIPT_PATH = ... / "scripts" / "arm_simulate.py"`. NEVER `from scripts.arm_simulate import main` (Phase 10 may relocate; scripts/ is intentionally not a Python package — see `tests/test_amortize.py:766-768`).

### Fixture-as-source with citation comments

**Source:** Every Phase 1+2+3+4 fixture — `tests/fixtures/golden_pmt.json:6` (`"source": "https://en.wikipedia.org/wiki/Mortgage_calculator"`), `tests/fixtures/affordability/*.json` (per-fixture `notes` + `source` blocks).

**Apply to:** Every `tests/fixtures/arm/*.json` includes `"source": "ROADMAP.md SC-N"` or Selling Guide citation; every `tests/fixtures/arm/oracle/*.json` includes `"source": "https://www.bankrate.com/...  (captured 2026-MM-DD)"` per CONTEXT.md D-04 annual re-capture cadence.

---

## No Analog Found

| File | Role | Reason |
|---|---|---|
| `references/arm-mechanics.md` | reference doc | No `references/*.md` files exist in the codebase yet (only `data/reference/*.yml`). Phase 5 establishes the new doc style. RESEARCH §Q4 + CONTEXT.md D-08 [REVISED] specify content; format-style is planner's discretion. |
| `tests/fixtures/arm/oracle/*.pdf` | binary capture artifact | No committed binary capture artifacts exist in the codebase. CONTEXT.md D-04 [REVISED] establishes the new `<source>_<product>_capture_2026.pdf` + `.json` pair convention. |
| `scripts/_cli_helpers.py` (factor) | shared utility module | No `scripts/_*.py` shared modules exist (only `scripts/amortize.py` + `scripts/affordability.py` + `scripts/hooks/`). Phase 5 establishes the convention; `lib/money.py` provides the closest naming/import-discipline analog. |

---

## Metadata

**Analog search scope:** `lib/`, `scripts/`, `tests/`, `tests/fixtures/`, `data/reference/`, `references/`, `.planning/phases/05-arm-modeling/`.

**Files scanned:** `lib/affordability.py` (1513 lines), `lib/amortize.py` (498 lines), `lib/models.py` (91 lines), `lib/money.py` (46 lines), `scripts/affordability.py` (320 lines), `scripts/amortize.py` (238 lines), `tests/conftest.py` (70 lines), `tests/test_affordability.py` (1653 lines, targeted reads), `tests/test_amortize.py` (1067 lines, targeted reads), `tests/fixtures/golden_pmt.json` (45 lines), `tests/fixtures/affordability/*.json` (directory listing only — 10 files), `tests/fixtures/amortize/*.json` (directory listing only — 7 files), `data/reference/*.yml` (directory listing only — 10 files), `.planning/phases/05-arm-modeling/05-CONTEXT.md` (458 lines), `.planning/phases/05-arm-modeling/05-RESEARCH.md` (760 lines, targeted sections).

**Pattern extraction date:** 2026-04-30.

**Strong-match coverage:** 12 of 14 files have an exact or composite analog with copyable excerpts. The 2 weak-analog cases (`references/arm-mechanics.md` and the oracle PDF/JSON capture pairs) are explicitly RESEARCH-driven per RESEARCH §Q3 + Q4 + CONTEXT.md D-04 [REVISED] + D-08 [REVISED]; the planner uses RESEARCH.md content directly, not codebase patterns.

**Related canonical excerpts (line-pinned for the planner to lift):**
- ARMRequest cross-field validator: see RESEARCH lines 488-518 (Code Example 1) — analog skeleton from `lib/amortize.py:184-194`
- build_arm_schedule per-epoch slice-stitch: see RESEARCH lines 520-632 (Code Example 2) — analog from `lib/amortize.py:295-383`
- 6-key envelope construction for arm_simulate.py: lift `scripts/affordability.py:236-274` verbatim
- _find_json_float_loc factor target: lift `scripts/affordability.py:70-123` verbatim → `scripts/_cli_helpers.py::find_json_float_loc`
- _quantize_rate promotion source: lift `lib/affordability.py:613-627` verbatim → `lib/money.py::quantize_rate`
- arm_fixture loader: clone `tests/conftest.py:38-52` shape, swap "amortize" → "arm"
- Lazy-import test harness: clone `tests/test_affordability.py:1194-1242` body, swap module name
- Citation-coverage meta-test: adapt `tests/test_affordability.py:1154-1191` shape, swap to `applied_cap` Literal coverage
