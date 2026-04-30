# Phase 4: Affordability — Pattern Map

**Mapped:** 2026-04-30
**Phase:** 04-affordability
**Files analyzed:** 12 (4 created, 1 modified, 7 fixture JSONs created)
**Analogs found:** 12 / 12 (every new file has a strong existing analog)

## Summary

Phase 4 is pure composition over Phase 1 (`lib/models.py`, `lib/money.py`, `tests/conftest.py`, `config/household.example.yml`), Phase 2 (`lib/rules/*` predicates + `_loader.py` warnings) and Phase 3 (`lib/amortize.py`, `scripts/amortize.py`, `tests/test_amortize.py`, `tests/fixtures/amortize/*.json`). Every new file has a near-1:1 analog in the existing tree; the planner can lift patterns largely unmodified. The three Phase 2 predicate-signature drifts surfaced in RESEARCH (`loan_type.classify` requires `program=`; `conventional_pmi.status` takes `(loan, scheduled_balance, original_property_value, ...)` not `(ltv_pct, ...)`; `fha_mip.compute` takes `(loan, original_property_value, endorsement_date)` not `(loan_amount, ltv_pct, term_months)`) are called out in `## Watch Out For` and must be honored verbatim when the planner writes plan tasks.

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `lib/affordability.py` | calc-engine module + Pydantic request/response models | request-response (in-process) | `lib/amortize.py` | exact (same shape: AmortizeRequest + pure function + lib.money + lib.models composition) |
| `scripts/affordability.py` | CLI wrapper | request-response (subprocess JSON-in/JSON-out) | `scripts/amortize.py` | exact (D-13 explicitly mirrors Phase 3 D-17/18/19) |
| `tests/test_affordability.py` | unit + integration tests | golden + structural + invariant + CLI subprocess | `tests/test_amortize.py` | exact |
| `tests/fixtures/affordability/forward_*.json` (5 files) | golden fixture JSON | data-only | `tests/fixtures/amortize/biweekly_true_200k_6_5.json` | exact (per-fixture-per-file pattern) |
| `tests/fixtures/affordability/reverse_conventional_80_ltv_43_dti.json` | golden fixture JSON (round-trip anchor) | data-only | `tests/fixtures/amortize/biweekly_true_200k_6_5.json` | exact |
| `tests/fixtures/affordability/joint_applicants_two_incomes.json` | golden fixture JSON | data-only | `tests/fixtures/amortize/biweekly_true_200k_6_5.json` | exact |
| `tests/fixtures/affordability/single_applicant.json` | golden fixture JSON | data-only | `tests/fixtures/amortize/biweekly_true_200k_6_5.json` | exact |
| `tests/fixtures/affordability/household_example_yml_e2e.json` | golden fixture JSON (SC-4 invocation manifest) | data-only | `tests/fixtures/amortize/biweekly_true_200k_6_5.json` | role-match (manifest pattern is new but fixture-loading shape preserved) |
| `tests/conftest.py` (MODIFY) | pytest fixture factory | request-response | existing `amortize_fixture` factory in same file | exact (extend with sibling factory) |
| `config/household.example.yml` (MODIFY) | User-Layer YAML schema | data-only | itself (Phase 1 skeleton) | exact (extend in place per D-15) |

## Pattern Assignments

### `lib/affordability.py` (calc-engine module + Pydantic request/response models)

**Analog:** `lib/amortize.py` (Phase 3) — same role (calc-engine wrapping numpy-financial), same data flow (Pydantic request → pure function → frozen Pydantic response), same import discipline (lib.models + lib.money + numpy_financial composition).

**Module docstring shape (lines 1-49 of `lib/amortize.py`):**

```python
"""Schedule generator wrapping numpy-financial PMT/IPMT/PPMT (AMRT-01).

Per AMRT-01, this module wraps numpy-financial — it does NOT reimplement amortization math.
[...]
LOCKED DECISION - D-04 (rate-per-period conversion; per CONTEXT.md):
  Monthly:           period_rate = annual_rate / Decimal("12").
  All conversions stay in Decimal — never go through float.

numpy-financial bug avoidance:
  - Bug #130 (npf.pmt fv-sign flipped when fv != 0):
      We always pass fv=0 (default). Phase 3 has no balloon-mortgage path.
"""
```

**Phase 4 adaptation:** docstring header cites AFFD-01..09; enumerate D-01..D-18 from CONTEXT.md as "LOCKED DECISION" blocks; document the 3 predicate-signature corrections from RESEARCH; pin the `target_loan_type → program` cross-walk + `target_loan_type → 8-value LoanType` acceptance table (RESEARCH Open Question #3).

**Imports pattern (lines 138-153 of `lib/amortize.py`):**

```python
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

import numpy_financial as npf
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.models import Loan, Payment, Schedule
from lib.money import quantize_cents

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date
```

**Phase 4 adaptation:** keep the same skeleton; ADD selective full-path imports for every Phase 2 predicate (Phase 2 D-08 — full-path imports, no re-exports):

```python
# Phase 2 predicates — full-path import per Phase 2 D-08 (one predicate per citation)
from lib.rules.loan_type import classify as loan_type_classify, MissingCountyDataError
from lib.rules.conventional_pmi import (
    LTV_AUTO_TERMINATE,
    LTV_REQUEST_ELIGIBLE,
    status as conventional_pmi_status,
)
from lib.rules.fha_mip import compute as fha_mip_compute, MIPResult
from lib.rules.va_funding_fee import compute as va_funding_fee_compute
from lib.rules.va_residual_income import (
    evaluate as va_residual_evaluate,
    ResidualIncomeResult,
)
from lib.rules.usda import evaluate as usda_evaluate, USDAEligibilityResult
from lib.rules.atr_qm import general_qm_passes
from lib.rules.fannie_eligibility import compute_llpa as fannie_compute_llpa
from lib.rules.freddie_eligibility import evaluate as freddie_evaluate
from lib.rules._loader import StaleReferenceWarning  # for warnings.catch_warnings propagation
from lib.rules.types import County, LoanType, Region
```

**Pydantic v2 strict + frozen + extra=forbid model pattern (lines 156-194 of `lib/amortize.py`):**

```python
class ExtraPrincipalEntry(BaseModel):
    """One extra-principal entry (D-05).
    [...]
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    period: int = Field(ge=1)
    amount: Decimal = Field(strict=True, gt=Decimal("0"), max_digits=14, decimal_places=2)
    recurring: bool = False


class AmortizeRequest(BaseModel):
    """Top-level request schema for scripts/amortize.py (D-19 boundary)."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    loan: Loan
    frequency: Literal["monthly", "biweekly"] = "monthly"
    biweekly_mode: Literal["true", "half-monthly"] | None = None
    extra_principal: list[ExtraPrincipalEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _biweekly_mode_consistency(self) -> AmortizeRequest:
        if self.frequency == "monthly" and self.biweekly_mode is not None:
            raise ValueError("biweekly_mode must be None when frequency='monthly' (D-02)")
        return self
```

**Phase 4 adaptation:** new Pydantic models follow this exact shape (`Applicant`, `Household`, `EscrowInputs`, `VAInputs`, `AffordabilityRequest`, `AffordabilityResponse`). Use `Money` and `Rate` aliases from `lib.models`. Use `model_validator(mode="after")` for cross-field validators (e.g., `if target_loan_type == "va" and self.va is None: raise ValueError(...)` per RESEARCH Open Question #7). For the `mode: forward | reverse` discriminator (D-14), prefer Pydantic's `Field(discriminator="mode")` over a single merged model with optional fields.

**Pure-function entrypoint pattern (lines 255-292 of `lib/amortize.py`):**

```python
def build_schedule(
    loan: Loan,
    *,
    frequency: Literal["monthly", "biweekly"] = "monthly",
    biweekly_mode: Literal["true", "half-monthly"] | None = None,
    extra_principal: Sequence[ExtraPrincipalEntry] = (),
) -> Schedule:
    """Generate an amortization schedule (AMRT-02..05).
    [...]
    """
    [...]
    if frequency == "monthly":
        return _build_fixed_monthly(loan, origination, extra_principal)
    [...]
```

**Phase 4 adaptation:** ship two top-level pure functions per the stable downstream contract documented in CONTEXT.md `<code_context>` line 279: `evaluate_forward(request: AffordabilityRequest) -> AffordabilityResponse` and `evaluate_reverse(request: AffordabilityRequest) -> AffordabilityResponse`. Plus internal helpers: `_compute_dti(...)`, `_compute_ltv(...)`, `_compute_cltv(...)`, `_compute_piti(...)`, `_classify_target_loan_type(...)` (cross-walk per RESEARCH Open Question #3), `_evaluate_blockers(...)` (precedence pipeline per D-11).

**numpy-financial use pattern (`lib/amortize.py:308`, contrasted with Phase 4 reverse):**

```python
# Phase 3 forward (npf.pmt with sign flip):
level_pmt = quantize_cents(-npf.pmt(period_rate, loan.term_months, loan.principal))

# Phase 4 reverse (npf.pv with sign flip; from RESEARCH §"numpy-financial npf.pv"):
monthly_rate = annual_rate / Decimal("12")
raw_pv = npf.pv(rate=monthly_rate, nper=term_months, pmt=-max_pi, fv=0)
max_loan_amount = quantize_cents(-raw_pv)
```

**Phase 4 adaptation:** `evaluate_reverse` calls `npf.pv` directly (NOT through `build_schedule`); always passes `fv=0` (Phase 3 D-09 + numpy-financial bug #130 avoidance, already documented in `lib/amortize.py:124-127`); converts `pmt` to negative + flips the returned `pv` sign to make it a positive principal-received Decimal; runs `quantize_cents(...)` ONCE end-of-period.

**Decimal-discipline pattern (`lib/money.py:39-46` — single source of truth):**

```python
def quantize_cents(value: Decimal) -> Decimal:
    """Round a Decimal to two places using ROUND_HALF_UP.

    Call ONCE at end-of-period; never mid-calculation.
    """
    with localcontext(MONEY_CONTEXT):
        return value.quantize(CENT, rounding=ROUND_HALF_UP)
```

**Phase 4 adaptation:** EVERY money output in `lib/affordability.py` (PITI, monthly_pi, monthly_mi, max_loan_amount, dti_front, dti_back) flows through `quantize_cents`. PITI sum is rounded ONCE at the end (Phase 3 PITFALLS pattern documented in `lib/amortize.py:74-79`):

```python
# CORRECT — quantize the sum:
piti_pre_quantize = monthly_pi + monthly_tax + monthly_insurance + monthly_hoa + monthly_mi
piti = quantize_cents(piti_pre_quantize)

# WRONG — would compound rounding errors (do NOT do this):
# piti = quantize_cents(monthly_pi) + quantize_cents(monthly_tax) + ...
```

**Warning capture pattern (RESEARCH §"_loader.py" — for D-11 stale-warning propagation):**

```python
import warnings
from lib.rules._loader import StaleReferenceWarning

with warnings.catch_warnings(record=True) as captured:
    warnings.simplefilter("always", StaleReferenceWarning)
    # ... call predicates that touch fha-mip-rates.yml or va-residual-income.yml ...
    response_warnings: list[str] = [str(w.message) for w in captured]
```

**Phase 4 adaptation:** wrap every predicate call site in this `catch_warnings` block; propagate the `str(w.message)` strings into `response.warnings` (per CONTEXT.md D-11). RESEARCH notes both `fha-mip-rates.yml` (effective 2023-03-20) AND `va-residual-income.yml` (effective 2023-04-07) currently fire `StaleReferenceWarning` — every FHA or VA evaluation will surface a stale-warning string, which is documented expected behavior.

---

### `scripts/affordability.py` (CLI wrapper)

**Analog:** `scripts/amortize.py` (Phase 3) — exact same role (JSON-in/JSON-out CLI), exact same conventions (D-13 explicitly says "mirror Phase 3 D-17/18/19").

**Argparse + sys.path skeleton (lines 125-160 of `scripts/amortize.py`):**

```python
def main() -> int:
    parser = argparse.ArgumentParser(
        prog="amortize",
        description="Generate an amortization schedule from a JSON loan input.",
        epilog=(
            "Input JSON shape: a Loan object plus optional 'frequency' "
            '("monthly"|"biweekly"; default "monthly"), [...]. '
            'All money/rate fields MUST be JSON strings (e.g. "400000.00"); '
            "Pydantic v2 strict mode rejects JSON floats at the boundary."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to JSON file containing the loan input.",
    )
    args = parser.parse_args()

    # When invoked as a script (`python scripts/amortize.py ...`), Python puts
    # `scripts/` on sys.path, NOT the project root, so `from lib.amortize import ...`
    # fails with ModuleNotFoundError. Insert the project root [...].
    _project_root = str(Path(__file__).resolve().parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    # lazy-import per D-18: heavy deps (numpy_financial, dateutil, lib.amortize)
    # are NOT loaded on the --help fast path.
    from lib.amortize import AmortizeRequest, build_schedule
    from pydantic import ValidationError
```

**Phase 4 adaptation:** `prog="affordability"`; epilog enumerates the discriminator `mode` field + the per-mode required fields per CONTEXT.md D-10; lazy-import `from lib.affordability import AffordabilityRequest, evaluate_forward, evaluate_reverse`. Per CONTEXT.md `<code_context>` line 270, lazy-import `numpy_financial` ONLY when `mode == "reverse"` (forward mode goes through `build_schedule` which already imports it).

**Pre-validation float gate pattern (lines 72-122 of `scripts/amortize.py`):**

```python
def _find_json_float_loc(raw: str) -> tuple[list[str | int], str] | None:
    """Walk parsed JSON and return (loc-path, decimal-string) of the first JSON float.
    [...]
    The schema has zero fields that legitimately accept JSON floats:
      - principal / annual_rate / amount: must be JSON strings (Money/Rate)
      - term_months / period: JSON integers
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

**Phase 4 adaptation:** lift verbatim — Phase 4's request schema also has zero fields that legitimately accept JSON floats (loan_amount, property_value, down_payment, max_dti, target_ltv_pct, annual_rate, monthly_pmi, gross_monthly_income, monthly debts, escrow.{property_tax_monthly, insurance_monthly, hoa_monthly}, va.actual_residual_income — all Money/Rate strings; term_months / family_size / credit_score / unit_count are JSON ints).

**6-key Pydantic envelope pattern (lines 36-60 docstring + lines 187-214 of `scripts/amortize.py`):**

```python
"""Envelope Shape Contract (WR-02 closure):
  All ValidationError-class boundary surfaces emit a uniform 6-key Pydantic v2
  e.json() envelope on stderr:
    [{"type": "<error_type>", "loc": [<JSON-pointer>],
      "msg": "<message>",     "input": "<offending_value>",
      "url": "<docs_url>",    "ctx": {"class": "<...>", ...}}]
"""

# ... in main() body ...
float_hit = _find_json_float_loc(raw)
if float_hit is not None:
    float_loc, float_input = float_hit
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

try:
    request = AmortizeRequest.model_validate_json(raw)
except ValidationError as e:
    print(e.json(), file=sys.stderr)
    return 2
```

**Phase 4 adaptation:** identical shape; substitute `AffordabilityRequest`. Plus dispatch on `request.mode` AFTER Pydantic validation:

```python
if request.mode == "forward":
    response = evaluate_forward(request)
else:  # reverse
    response = evaluate_reverse(request)
print(response.model_dump_json(indent=2))
return 0
```

**File error handling pattern (lines 162-175 of `scripts/amortize.py`):**

```python
try:
    raw = args.input.read_text()
except FileNotFoundError as e:
    print(
        json.dumps({"error": f"input file not found: {e.filename}"}),
        file=sys.stderr,
    )
    return 2
except OSError as e:
    print(
        json.dumps({"error": f"could not read input file: {e}"}),
        file=sys.stderr,
    )
    return 2
```

**Phase 4 adaptation:** lift verbatim — the `{"error": "..."}` simpler shape is the documented exception (Phase 3 envelope contract intentionally scopes the 6-key shape to ValidationError surfaces only; file-not-found stays simple).

---

### `tests/test_affordability.py` (unit + integration tests)

**Analog:** `tests/test_amortize.py` (Phase 3) — exact same shape: golden + structural + invariant + CLI subprocess + boundary-validator coverage.

**SCRIPT_PATH constant pattern (lines 50-53 of `tests/test_amortize.py`):**

```python
AMORTIZE_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "amortize.py"
SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "amortize.py"
"""Phase 3 CLI lives at project root scripts/. Phase 10 will relocate to
.claude/skills/mortgage-ops/scripts/; only this constant updates."""
```

**Phase 4 adaptation:** mirror with `AFFORDABILITY_MODULE_PATH` + `SCRIPT_PATH = ... / "affordability.py"`; same Phase 10 relocation comment so a single-constant edit absorbs the move.

**Subprocess invocation pattern (lines 722-751 of `tests/test_amortize.py`):**

```python
def test_cli_smoke_subprocess_round_trip(tmp_path: Path) -> None:
    """AMRT-06: write input JSON, invoke script via subprocess, parse output JSON."""
    input_path = tmp_path / "loan.json"
    input_path.write_text(
        json.dumps(
            {
                "loan": {
                    "principal": "200000.00",
                    "annual_rate": "0.065000",
                    "term_months": 360,
                    "origination_date": "2026-05-01",
                },
            }
        )
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(input_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["monthly_pi"] == "1264.14"
    assert out["payments"][-1]["balance"] == "0.00"
```

**Phase 4 adaptation:** AFFD-08 CLI smoke writes a forward-mode + a reverse-mode JSON to `tmp_path`; subprocess; assert response shape (Pydantic schema match) + `blocked_by` strings + dollar amounts. Phase 4 must NOT use `import scripts.affordability` directly — subprocess only (Phase 3 D-17 portability discipline; CONTEXT.md `<code_context>` line 282).

**Lazy-import `--help` test pattern (lines 754-827 of `tests/test_amortize.py`):**

```python
def test_cli_help_does_not_import_lib_amortize() -> None:
    """D-18: --help must not trigger lib.amortize import (lazy-import contract).
    [...]
    Spawn a fresh Python subprocess (so lib.amortize is NOT already imported [...])
    and run an inline check that loads scripts/amortize.py via
    importlib.util.spec_from_file_location with sys.argv patched to --help.
    """
    project_root = Path(__file__).resolve().parent.parent
    inline = (
        "import importlib.util, sys, json\n"
        f"sys.path.insert(0, {str(project_root)!r})\n"
        f"SCRIPT = {str(SCRIPT_PATH)!r}\n"
        "spec = importlib.util.spec_from_file_location('scripts_amortize', SCRIPT)\n"
        "[...]"
        "result = {\n"
        "    'help_exit_code': exit_code,\n"
        "    'lib_amortize_imported': 'lib.amortize' in sys.modules,\n"
        "    'numpy_financial_imported': 'numpy_financial' in sys.modules,\n"
        "}\n"
        "print(json.dumps(result))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", inline],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["help_exit_code"] == 0
    assert payload["lib_amortize_imported"] is False
    assert payload["numpy_financial_imported"] is False
```

**Phase 4 adaptation:** substitute `lib.affordability` + verify both `lib.affordability` AND `numpy_financial` are NOT in `sys.modules` after `--help` exits (D-13 inherits Phase 3 D-18).

**6-key envelope test pattern (lines 873-928 of `tests/test_amortize.py`):**

```python
def test_cli_rejects_float_principal(tmp_path: Path) -> None:
    """D-19 + WR-02: pre-validation gate emits the full 6-key Pydantic-shaped envelope.
    [...]
    Pinned values:
      - type:  decimal_type
      - loc:   ['loan', 'principal']
      - input: '400000.00'
      - url:   starts with https://errors.pydantic.dev/ and ends with /v/decimal_type
    """
    bad = tmp_path / "float.json"
    bad.write_text(
        '{"loan": {"principal": 400000.00, "annual_rate": "0.065000", "term_months": 360}}'
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

    # 6-key uniform shape (WR-02 closure)
    assert set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}
    assert err["type"] == "decimal_type"
    assert err["loc"] == ["loan", "principal"]
    assert err["input"] == "400000.00"
    assert err["url"].startswith("https://errors.pydantic.dev/")
    assert err["url"].endswith("/v/decimal_type")
    assert err["ctx"].get("class") == "Decimal"
```

**Phase 4 adaptation:** drop floats into `loan_amount`, `property_value`, `max_dti`, `annual_rate`, `escrow.property_tax_monthly`, `va.actual_residual_income`; assert the same 6-key shape and the loc-path (e.g., `["escrow", "property_tax_monthly"]`).

**Decimal-from-strings test pattern (lines 121-129 of `tests/test_amortize.py`):**

```python
@pytest.mark.parametrize(
    "fixture_id",
    [pytest.param(fid, id=fid) for fid in FOUR_ORACLE_IDS],
)
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
    schedule = build_schedule(loan)
    assert schedule.monthly_pi == Decimal(fx["expected_monthly_pi"])
```

**Phase 4 adaptation:** every fixture money field is a quoted string; parse via `Decimal(fx["..."])`; compare with `==` (NEVER `pytest.approx` or `assertAlmostEqual` — CLAUDE.md money discipline + D-18). The ONLY `Decimal("0.0001")` tolerance is on the round-trip DTI math (D-09), and it applies ONLY to the rate value, not to dollar amounts (which compare with strict `==`).

**Round-trip invariant pattern (lines 56-75 of `tests/test_amortize.py`):**

```python
def assert_schedule_invariants(schedule: Schedule, original_principal: Decimal) -> None:
    """Asserts AMRT-07 + D-11 + D-15 invariants on every produced schedule.
    [...]
    """
    sum_principal = sum((p.principal for p in schedule.payments), start=Decimal("0.00"))
    sum_extra = sum((p.extra_principal for p in schedule.payments), start=Decimal("0.00"))
    assert sum_principal + sum_extra == original_principal
    assert schedule.payments[-1].balance == Decimal("0.00")
    assert schedule.total_interest == schedule.payments[-1].cumulative_interest
```

**Phase 4 adaptation:** ship a parallel `assert_affordability_invariants(response, request)` helper. Invariants:
- Forward: `response.dti_back >= response.dti_front` exactly; `response.cltv >= response.ltv` exactly; `response.piti == quantize_cents(monthly_pi + tax + ins + hoa + mi)` exactly.
- Reverse: round-trip closure per SC-2 / D-09: feed `response.max_loan_amount + request.down_payment` back through `evaluate_forward` and assert `forward.dti_back <= request.max_dti + Decimal("0.0001")`; assert `forward.loan_amount == reverse.max_loan_amount` exactly (Decimal equality on dollars).
- Both: `response.blocked is True` iff `response.blocked_by is not None`.

**VA-residual citation verbatim test pattern (RESEARCH §"va_residual_income.py" + Phase 2 D-11):**

```python
# from lib/rules/va_residual_income.py:115:
citation = f"VA-RESIDUAL-{region.upper()}-FAMILY-{family_size}"
```

**Phase 4 adaptation:** `tests/test_affordability.py::test_blocked_by_va_residual_west_family_4` MUST assert `response.blocked_by == "VA-RESIDUAL-WEST-FAMILY-4"` verbatim (matches ROADMAP SC-3 example + Phase 2 D-11 stable-citation contract). DO NOT format-drift; the predicate already emits this string and Phase 4 reads it through unchanged via `result.binding_rule_citation`.

---

### `tests/fixtures/affordability/*.json` (golden fixtures, 9 files)

**Analog:** `tests/fixtures/amortize/biweekly_true_200k_6_5.json` — same shape (one fixture per file; rich expected_summary block; `source` + `notes` annotations).

**Fixture skeleton (lines 1-45 of `tests/fixtures/amortize/biweekly_true_200k_6_5.json`):**

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "id": "biweekly_true_200k_6_5",
  "source": "scaled from Wikipedia oracle [...]; biweekly-true mode per CONTEXT.md D-01 + D-04",
  "rounding": "ROUND_HALF_UP",
  "notes": "True biweekly: rate/26 + half-of-monthly-pmt; accelerates payoff per RESEARCH 3.1. Engine-emitted values pasted verbatim.",
  "loan": {
    "principal": "200000.00",
    "annual_rate": "0.065000",
    "term_months": 360,
    "origination_date": "2026-05-01",
    "loan_type": "fixed"
  },
  "frequency": "biweekly",
  "biweekly_mode": "true",
  "extra_principal": [],
  "expected_schedule_summary": {
    "monthly_pi": "1264.14",
    "total_interest": "196339.36",
    [...]
  }
}
```

**Phase 4 adaptation per fixture:**
- Top-level keys: `$schema`, `id`, `source` (e.g., `"ROADMAP.md SC-3"` or `"hand-calc per AFFD-04 D-01"`), `rounding: "ROUND_HALF_UP"`, `notes` (citation references).
- Top-level `request:` block matches `AffordabilityRequest.model_dump()` shape (mode, household, max_dti, loan_amount/down_payment, etc., per D-10).
- Top-level `expected_response:` block matches `AffordabilityResponse.model_dump()` shape with money fields as quoted strings (Decimal-from-strings discipline).
- Citations land in `expected_response.blocked_by` verbatim — for the VA fixture, `"VA-RESIDUAL-WEST-FAMILY-4"`; for FHFA jumbo, the planner-finalized format like `"FHFA-LIMIT-CONFORMING-KING"`.

**Per-fixture quick spec:**

| Fixture | Mode | Anchor | Expected Output |
|---|---|---|---|
| `forward_conventional_80_ltv.json` | forward | $400k @ 6.5%/30yr (matches `computed_400k_30yr` oracle in `golden_pmt.json`) | `blocked: false`, `blocked_by: null`, `monthly_pi: "2528.27"` |
| `forward_conventional_85_ltv_with_pmi.json` | forward | LTV > 0.80 → caller-supplied `monthly_pmi` line item appears in PITI; `warnings: ["HPA-PMI-REQUIRED"]` |
| `forward_fha_above_dti_cap.json` | forward | DTI > max_dti | `blocked: true`, `blocked_by: "DTI-CAP-FHA"` (planner-finalized) |
| `forward_va_residual_fail.json` | forward | West / family-4, actual residual < $1,117 (RESEARCH `va-residual-income.yml` table) | `blocked: true`, `blocked_by: "VA-RESIDUAL-WEST-FAMILY-4"` (ROADMAP SC-3 verbatim) |
| `forward_jumbo_above_county_limit.json` | forward | conventional + loan_amount > King WA county limit | `blocked: true`, `blocked_by: "FHFA-LIMIT-CONFORMING-KING"` (planner-finalized) |
| `reverse_conventional_80_ltv_43_dti.json` | reverse | max_dti=0.43, target_ltv_pct=0.80, 7%/30yr | engine-emitted `max_loan_amount`; round-trips through forward within `Decimal("0.0001")` DTI tolerance per SC-2 |
| `joint_applicants_two_incomes.json` | forward | applicants=[A:credit 720, B:credit 680] | uses `min(720,680)=680` for Fannie/Freddie; income summed (SC-5) |
| `single_applicant.json` | forward | applicants=[only A] | identical code path; min reduces to A.credit_score (D-07) |
| `household_example_yml_e2e.json` | forward | manifest pointing at `config/household.example.yml` | full schema match per AFFD-09; subprocess invocation per SC-4 |

---

### `tests/conftest.py` (MODIFY — extend with `affordability_fixture` factory)

**Analog (in same file):** the existing `amortize_fixture` factory at lines 38-52.

**Existing factory pattern (lines 38-52 of `tests/conftest.py`):**

```python
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
```

**Phase 4 adaptation — append a sibling factory:**

```python
@pytest.fixture
def affordability_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single affordability fixture by filename
    stem from tests/fixtures/affordability/. Mirrors `amortize_fixture` —
    one-fixture-per-file shape; loader takes a filename stem like
    "forward_va_residual_fail", not an id within an array.

    Per CONTEXT.md D-17: every Phase 4 fixture lives under
    tests/fixtures/affordability/ as one .json per scenario.
    """

    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "affordability" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _load
```

The `FIXTURE_DIR` constant on line 19 already supports this; no other change to conftest.py.

---

### `config/household.example.yml` (MODIFY — extend in place per D-15)

**Analog:** itself (current Phase 1 redacted skeleton at the same path).

**Existing skeleton (full file — 36 lines):**

```yaml
# config/household.example.yml
#
# COMMITTED SKELETON — copy to config/household.yml and fill in your real values.
# config/household.yml is in the User Layer (per DATA_CONTRACT.md): gitignored
# and never auto-updated by any system process.
#
# Phase 4 (Affordability) consumes this schema. [...]

household:
  location:
    state: "WA"
    county: "King"            # Must match a county in data/reference/conforming-limits-*.yml
    zip: "00000"

  applicants:
    - name: "Applicant A"
      gross_monthly_income: "0.00"   # Decimal string
      credit_score: 0                # FICO 300-850
    - name: "Applicant B"
      gross_monthly_income: "0.00"
      credit_score: 0

  monthly_debts:
    auto: "0.00"
    student_loans: "0.00"
    credit_cards: "0.00"
    other: "0.00"

  current_housing_payment: "0.00"
```

**Phase 4 adaptation:** the existing block stays (D-15: extend, don't replace). The header comment block must be UPDATED to remove the "Phase 1 ships only this redacted example" hedge — Phase 4 is the FINAL revision per AFFD-09. Add field-level docstring comments per D-15 + RESEARCH amendment for FIPS:

```yaml
  location:
    state: "WA"                        # 2-letter state code (display only)
    state_fips: "53"                   # 2-digit FIPS (REQUIRED for County construction;
                                        # WA = 53; lookup at https://www.census.gov/library/reference/code-lists/ansi.html)
    county_fips: "033"                 # 3-digit FIPS (King WA = 033; consumed by
                                        # lib.rules.loan_type.classify + lib.rules.usda.evaluate)
    county_name: "King"                # Display name; documentation only (NOT a regulatory key)
    zip: "00000"

  applicants:
    - name: "Applicant A"              # Display name only, not a legal identifier
      gross_monthly_income: "0.00"     # Decimal string; D-06 sums across applicants
      credit_score: 0                  # FICO 300-850; D-05 picks min across applicants for
                                        # Fannie LLPA + Freddie eligibility (caller supplies their
                                        # representative middle-of-three; mid-of-3 modeling out
                                        # of v1 scope per CONTEXT.md D-05)
    [...]

  # NEW Phase 4 escrow block (D-01) — caller-supplied PITI components.
  # Caller enters monthly $ directly (no county-keyed % rates in v1; deferred to v2).
  escrow:
    property_tax_monthly: "0.00"       # Decimal string; consumed by AFFD-04 PITI composition
    insurance_monthly: "0.00"          # Decimal string; consumed by AFFD-04 PITI composition
    hoa_monthly: "0.00"                # Decimal string; default "0.00" when no HOA

  # Optional: VA-loan inputs (required when target_loan_type=="va"; per RESEARCH
  # Open Question #7, AffordabilityRequest fails fast via model_validator if
  # target_loan_type=="va" AND this block is missing).
  va:
    region: "west"                     # Literal["northeast","midwest","south","west"]
                                        # — consumed by lib.rules.va_residual_income.evaluate;
                                        # produces stable citation "VA-RESIDUAL-{REGION_UPPER}-FAMILY-{N}"
                                        # per Phase 2 D-11 (DO NOT format-drift)
    family_size: 4                     # int (>=1; sizes >5 add per_extra_member_increment)
    actual_residual_income: "0.00"     # Decimal string; current household residual income
                                        # to compare against the M26-7 table minimum
```

**File preservation:** `config/household.example.yml` is in the System Layer (committed; modified by Phase 4 per D-15 + DATA_CONTRACT.md). The User-Layer file `config/household.yml` is gitignored + protected by Phase 1's `scripts/hooks/block-user-layer.py` pre-commit hook (FND-04). The hook's allowlist already permits `*.example.yml` (CONTEXT.md D-16) — no hook change needed.

## Shared Patterns

### Money Discipline (applies to ALL `lib/affordability.py` math + ALL fixture money fields)

**Source:** `lib/money.py:39-46`

```python
def quantize_cents(value: Decimal) -> Decimal:
    with localcontext(MONEY_CONTEXT):
        return value.quantize(CENT, rounding=ROUND_HALF_UP)
```

**Apply to:** every Decimal-output money field (PITI, monthly_pi, monthly_mi, max_loan_amount, all DTI ratios, all LTV/CLTV ratios). Quantize ONCE at end-of-period; never mid-calculation. PITI sum = `quantize_cents(monthly_pi + tax + ins + hoa + mi)`, NOT sum-of-quantized-components (the latter compounds rounding errors).

### Pydantic v2 Strict + Frozen + extra=forbid (applies to ALL Phase 4 domain models)

**Source:** `lib/amortize.py:169` (and every Pydantic model in `lib/rules/*.py`)

```python
model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
```

**Apply to:** `Applicant`, `Household`, `EscrowInputs`, `VAInputs`, `AffordabilityRequest`, `AffordabilityResponse`, any helper models. `strict=True` rejects float into Money/Rate at validation time (catches the JSON-float foot-gun); `frozen=True` makes results immutable (composition discipline); `extra="forbid"` rejects typo'd field names (catches caller-side schema drift).

### Full-Path Predicate Imports (Phase 2 D-08; applies to ALL `lib/rules/*` use)

**Source:** Phase 2 D-08 + every `lib/rules/test_*.py`. Example from `tests/test_rules/test_va_residual_income.py:29`:

```python
from lib.rules.va_residual_income import ResidualIncomeResult, evaluate, minimum_required
```

**Apply to:** every Phase 2 predicate referenced by `lib/affordability.py`. NEVER `from lib.rules import va_residual_income` then `va_residual_income.evaluate(...)` — Phase 2 D-08 rejects re-exports.

### Stale-Reference Warning Capture (D-11 propagation into `response.warnings`)

**Source:** `lib/rules/_loader.py:34-38` (`StaleReferenceWarning` class) + `lib/rules/_loader.py:90-101` (the `warnings.warn(..., category=StaleReferenceWarning)` call site).

```python
class StaleReferenceWarning(UserWarning):
    """Emitted at module-load time when a reference YAML's effective date is
    more than 12 months in the past. Loud-by-default; never suppressed by
    library code."""
```

**Apply to:** every predicate call inside `lib/affordability.py`. Wrap in `warnings.catch_warnings(record=True)`; collect `str(w.message) for w in captured if issubclass(w.category, StaleReferenceWarning)`; append to `response.warnings`. Currently `fha-mip-rates.yml` (effective 2023-03-20) and `va-residual-income.yml` (effective 2023-04-07) both fire this warning on every load — Phase 4's response will surface stale strings on every FHA or VA evaluation. This is documented expected behavior; do not suppress.

### Hand-Calculated Golden Fixtures (FND-09 + Phase 2 + Phase 3 inheritance)

**Source:** `tests/fixtures/golden_pmt.json` + `tests/fixtures/amortize/biweekly_true_200k_6_5.json` + every `tests/fixtures/rules/*.json`. Common shape:

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "id": "...",
  "source": "https://... or 'computed in-tree' or 'ROADMAP.md SC-N'",
  "rounding": "ROUND_HALF_UP",
  "notes": "Hand-calc reasoning + citation references",
  ...
}
```

**Apply to:** all 9 Phase 4 fixtures. Money-field values quoted strings; comparisons use `Decimal(fx["..."])` parse + `==` exactly. The `Decimal("0.0001")` tolerance applies ONLY to the round-trip DTI rate (D-09), never to dollar amounts.

### CLI Subprocess Invocation in Tests (Phase 3 D-17 portability)

**Source:** `tests/test_amortize.py:50-53` + `tests/test_amortize.py:722-751`. Pattern: define `SCRIPT_PATH` constant; call `subprocess.run([sys.executable, str(SCRIPT_PATH), "--input", str(tmp_path/"x.json")], ...)`; never `import scripts.affordability` directly. This makes the Phase 10 relocation to `.claude/skills/mortgage-ops/scripts/` a one-line constant edit.

### Citation-Coverage Meta-Test (RUL-12/13 inheritance)

**Source:** `tests/test_rules/test_citation_coverage.py:15-48` (filesystem-introspecting parametrize over `lib/rules/*.py` predicate files).

**Apply to:** Phase 4 inherits this implicitly through D-17 — every `blocked_by` citation string format MUST have at least one fixture exercising it. RESEARCH §"Citation-coverage meta-test" recommends adding `tests/test_affordability.py::test_blocked_by_citation_coverage` that:
- Discovers all `BLOCKED_BY_*` constants exported from `lib/affordability.py`
- Asserts each is the `blocked_by` value of at least one fixture in `tests/fixtures/affordability/`
- For dynamic citations (VA-residual), regex-matches `r"^VA-RESIDUAL-(NORTHEAST|MIDWEST|SOUTH|WEST)-FAMILY-\d+$"` against at least one fixture's `blocked_by`

## Watch Out For

The three Phase 2 predicate-signature drifts surfaced in RESEARCH §"Phase 2 Predicate Signature Audit" are NOT optional. CONTEXT.md describes the predicates conceptually; the actual on-disk signatures differ. Plan tasks must call the predicates with the verified signatures below.

### 1. `loan_type.classify` requires the `program=` keyword (RESEARCH §"loan_type.py")

**On-disk signature** (verified at `lib/rules/loan_type.py:69-92`):

```python
def classify(
    loan_amount: Decimal,
    county: County | None,
    program: Literal["conventional", "fha", "va", "usda"] = "conventional",
    unit_count: int = 1,
) -> LoanType
```

**CONTEXT.md drift:** CONTEXT.md D-11 step 1 says `lib.rules.loan_type.classify(loan_amount, county)`. Actually requires `program` (defaults to `"conventional"`).

**Phase 4 fix:** derive `program` from `request.target_loan_type`:
- `target_loan_type in {"conventional", "jumbo"}` → `program="conventional"`
- `target_loan_type == "fha"` → `program="fha"`
- `target_loan_type == "va"` → `program="va"`
- `target_loan_type == "usda"` → `program="usda"`

Then map the 8-value `LoanType` return to acceptance per RESEARCH Open Question #3 cross-walk:
- `target=conventional` accepts `{conforming, high_balance}`, blocks on `jumbo` → `blocked_by="FHFA-LIMIT-CONFORMING-{COUNTY}"`
- `target=jumbo` accepts `{jumbo}` only
- `target=fha` accepts `{fha_standard, fha_high_balance}`
- `target=va` accepts `{va_standard, va_high_balance}`
- `target=usda` accepts `{usda}`

`MissingCountyDataError` (subclass of `ValueError`) is a HARD error (Pydantic envelope on stderr per Phase 3 D-19), NOT a `blocked_by` (per CONTEXT.md D-11 step 1).

### 2. `conventional_pmi.status` takes `(loan, scheduled_balance, original_property_value, ...)` (RESEARCH §"conventional_pmi.py")

**On-disk signature** (verified at `lib/rules/conventional_pmi.py:61-67`):

```python
def status(
    loan: Loan,
    scheduled_balance: Decimal,
    original_property_value: Decimal,
    is_high_risk: bool = False,
    months_elapsed: int | None = None,
) -> PMITerminationStatus  # Literal["auto_terminated","request_eligible","in_force","high_risk_midpoint_terminated"]
```

**CONTEXT.md drift:** D-02 says `conventional_pmi.status(ltv_pct, ...)`. Actual signature takes a `Loan` object + `scheduled_balance` + `original_property_value` (computes LTV internally). Returns a TERMINATION status enum, NOT a "needs PMI" boolean and NOT a PMI dollar amount.

**Phase 4 fix:** the predicate is the wrong question for affordability surface. Instead, use the exposed statutory constants directly (per RESEARCH §"conventional_pmi.py"):

```python
from lib.rules.conventional_pmi import LTV_REQUEST_ELIGIBLE  # Decimal("0.80")

origination_ltv = loan_amount / property_value
pmi_required_at_origination = origination_ltv > LTV_REQUEST_ELIGIBLE
```

**No PMI rate available from the predicate.** RESEARCH §"conventional_pmi.py" Assumption A5 + Open Question #1 flag this as the BIGGEST gap: there is no `pmi-rates.yml`. RESEARCH recommends caller-supplied `monthly_pmi: Decimal | None` request field, required when `target_loan_type=="conventional"` AND origination LTV > 0.80; document in `--help` and module docstring. The planner MUST resolve this at PLAN time. (For UFMIP / FHA MIP / VA funding fee, the predicates DO produce dollar amounts — only conventional PMI lacks rate sourcing.)

### 3. `fha_mip.compute` takes `(loan, original_property_value, endorsement_date)` (RESEARCH §"fha_mip.py")

**On-disk signature** (verified at `lib/rules/fha_mip.py:66-70`):

```python
def compute(
    loan: Loan,
    original_property_value: Decimal,
    endorsement_date: date,
) -> MIPResult  # ufmip: Decimal, annual_mip_pct: Decimal, terminates_at_period: int | Literal["life_of_loan"]
```

**CONTEXT.md drift:** D-02 says `fha_mip.compute(loan_amount, ltv_pct, term_months)`. Actual signature takes a `Loan` + `original_property_value` + `endorsement_date` (raises `NotImplementedError` for dates before 2023-03-20).

**Phase 4 fix:** construct a `Loan` and pass it:

```python
loan = Loan(
    principal=loan_amount,
    annual_rate=annual_rate,
    term_months=term_months,
    origination_date=date.today(),  # or caller-supplied per RESEARCH Open Question #6
)
mip = fha_mip_compute(
    loan=loan,
    original_property_value=property_value,
    endorsement_date=date.today(),  # default; can be optional request field
)
monthly_mip = quantize_cents((loan.principal * mip.annual_mip_pct) / Decimal("12"))
```

`MIPResult.annual_mip_pct` is a fractional Decimal like `Decimal("0.0055")` (= 55 bps). RESEARCH §"FHA UFMIP Financing Convention" recommends auto-financing UFMIP into principal (D-03 option (b)); when adopted, the `Loan.principal` passed above is `request.loan_amount + mip.ufmip` and the schedule amortizes the financed total.

### 4. Other surface details

- **`compute_llpa` + `freddie_evaluate` LTV-percentage-points convention** (RESEARCH §"fannie_eligibility.py" line 246): Fannie/Freddie predicates take `ltv_pct` AS PERCENTAGE POINTS (`Decimal("80.00")` for 80% LTV), NOT as a fraction (`Decimal("0.80")`). Phase 4 must multiply the fractional LTV by 100 AND quantize to 2 decimal places before calling either predicate (the predicates raise `ValueError` on >2-decimal input).
- **`loan_type.classify` raises `MissingCountyDataError` only when `loan_amount > baseline` AND `county is None`.** Loans at or below baseline can classify without county (returns `"conforming"` directly). Phase 4 must construct a `County(state_fips, county_fips, name)` from the household.location FIPS (RESEARCH amendment to D-15: add explicit FIPS to `household.example.yml`).
- **Subprocess invocation, NEVER `import scripts.affordability`** (Phase 3 D-17): `scripts/` has no `__init__.py` and is intentionally not a Python package. The Phase 4 CLI test that asserts the lazy-import contract uses `importlib.util.spec_from_file_location` (mirrors `tests/test_amortize.py::test_cli_help_does_not_import_lib_amortize`).
- **Fixture money equality is strict `==`, never tolerance.** D-18 reinforced. The ONLY tolerance applies to the round-trip DTI rate per D-09, and it is `Decimal("0.0001")` not float-epsilon.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| (none) | — | — | Every Phase 4 file has a strong existing analog. Phase 4 is pure composition over Phase 1/2/3. |

## Metadata

**Analog search scope:** `lib/`, `lib/rules/`, `scripts/`, `tests/`, `tests/fixtures/`, `tests/test_rules/`, `config/`, `data/reference/`.
**Files scanned:** ~30 (full read of `lib/amortize.py`, `lib/money.py`, `lib/models.py`, `scripts/amortize.py`, `tests/conftest.py`, `tests/test_amortize.py`, `tests/test_rules/test_va_residual_income.py`, `tests/test_rules/test_citation_coverage.py`, `lib/rules/_loader.py`, `lib/rules/loan_type.py`, `lib/rules/conventional_pmi.py`, `lib/rules/fha_mip.py`, `lib/rules/va_residual_income.py`, `lib/rules/va_funding_fee.py`, `lib/rules/usda.py`, `lib/rules/atr_qm.py`, `lib/rules/fannie_eligibility.py`, `lib/rules/freddie_eligibility.py`, `lib/rules/types.py`, `config/household.example.yml`, `tests/fixtures/golden_pmt.json`, `tests/fixtures/amortize/biweekly_true_200k_6_5.json`, `tests/fixtures/rules/conventional_pmi_in_force_81ltv.json`).
**Pattern extraction date:** 2026-04-30
**Confidence:** HIGH — every analog verified via direct source-read; predicate-signature drifts cross-checked against RESEARCH §"Phase 2 Predicate Signature Audit".

## PATTERN MAPPING COMPLETE
