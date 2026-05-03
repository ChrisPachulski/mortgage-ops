---
phase: 07
plan: 05
type: execute
wave: 5
depends_on: ["07-04"]
files_modified:
  - tests/test_apr.py
  - tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json
  - tests/fixtures/apr/regz_appendix_j_odd_first_period_15_days.json
  - tests/fixtures/apr/regz_appendix_j_odd_first_period_45_days.json
  - tests/fixtures/apr/regz_appendix_j_unit_period_monthly_regular.json
autonomous: true
requirements: [APR-05]
tags:
  - phase-07
  - estimated-apr
  - tests
  - fixtures
must_haves:
  truths:
    - "tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json exists with correct request shape"
    - "Wave 0 stub test_apr_reg_z_appendix_j_worked_example_returns_12_percent flips to PASS"
    - "Wave 0 stub test_newton_raphson_iterations_under_50_for_all_fixtures flips to PASS"
    - "tests/test_apr.py adds parametric per-fixture coverage iterating all hand-calc fixtures"
    - "All shipped fixtures have hand-verified expected_apr values within Decimal('0.00001') of solver output"
  artifacts:
    - path: "tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json"
      provides: "SC-1 anchor fixture: $5000 / 36 / $166.07 → 12.00% APR"
    - path: "tests/fixtures/apr/regz_appendix_j_odd_first_period_15_days.json"
      provides: "Wave 3 odd-first-period helper fixture coverage"
    - path: "tests/fixtures/apr/regz_appendix_j_odd_first_period_45_days.json"
      provides: "Long odd first period (1.5 unit periods worth — boundary)"
    - path: "tests/fixtures/apr/regz_appendix_j_unit_period_monthly_regular.json"
      provides: "Sanity: standard 6.5%/30yr Wikipedia anchor in APR shape"
    - path: "tests/test_apr.py"
      provides: "Parametric per-fixture coverage + iteration-cap assertions"
---

## Goal

Ship the Reg Z hand-calc anchor fixture (the SC-1 anchor) plus 3 sibling
hand-calc fixtures (odd-first-period 15-day, 45-day, regular monthly).
Flip Wave 0 stubs `test_apr_reg_z_appendix_j_worked_example_returns_12_percent`
and `test_newton_raphson_iterations_under_50_for_all_fixtures`. Add
parametric per-fixture coverage iterating all Phase 7 hand-calc fixtures.

## Tasks

### Task 1 — Ship `regz_appendix_j_5000_36_166_07.json` (SC-1 anchor)

```json
{
  "description": "Reg Z Appendix J Example J-1 — $5,000 / 36 monthly $166.07 → 12.00% APR. SC-1 anchor.",
  "citation": "12 CFR Part 1026 Appendix J §(c)(1)",
  "request": {
    "loan": {
      "principal": "5000.00",
      "annual_rate": "0.120000",
      "term_months": 36,
      "loan_type": "fixed"
    },
    "finance_charges": "0.00",
    "advance_schedule": [
      {"unit_period_offset": 0, "amount": "5000.00"}
    ],
    "payment_schedule": [
      {"starting_unit_period": 1, "periods": 36, "amount": "166.07"}
    ],
    "day_count": "30/360",
    "unit_periods_per_year": 12,
    "odd_first_period_days": 0
  },
  "expected": {
    "estimated_apr": "0.120000",
    "iterations_max": 5,
    "tolerance_used": "0.00001",
    "note": "Reg Z Appendix J Example J-1 — exact 12.00% APR within Decimal('0.00001')"
  }
}
```

### Task 2 — Ship `regz_appendix_j_odd_first_period_15_days.json`

```json
{
  "description": "15-day odd first period on Wikipedia $200k/30yr/6.5% — APR pushed above 6.50%.",
  "citation": "12 CFR §1026.17(c)(4) + Appendix J §(b)(5)(iii)",
  "request": {
    "loan": {
      "principal": "200000.00",
      "annual_rate": "0.065000",
      "term_months": 360,
      "origination_date": "2026-01-01",
      "loan_type": "fixed"
    },
    "finance_charges": "0.00",
    "advance_schedule": [
      {"unit_period_offset": 0, "amount": "200000.00"}
    ],
    "payment_schedule": [
      {"starting_unit_period": 1, "periods": 360, "amount": "1264.14"}
    ],
    "day_count": "30/360",
    "unit_periods_per_year": 12,
    "odd_first_period_days": 15
  },
  "expected": {
    "estimated_apr_min": "0.065100",
    "estimated_apr_max": "0.065500",
    "iterations_max": 10,
    "note": "Hand-calc gives APR ≈ 6.523%. The exact value is engine-computed and pinned by sibling test."
  }
}
```

(NOTE: per Phase 4 04-06 idiom — engine-emitted Decimal-string values
are pinned at first compute and the JSON `expected_apr` is set to the
engine's exact output. Plan execution captures `solve_apr` output and
writes it back into the fixture as `expected.estimated_apr` to seal.)

### Task 3 — Ship `regz_appendix_j_odd_first_period_45_days.json`

Same Wikipedia anchor, `odd_first_period_days=45`. Expected APR pushed
to ~6.547%. Captures the boundary case where `f = 45/30 = 1.5` would
violate D-16; test asserts that the request raises ValueError at
`_compute_odd_first_period_fraction` with the documented "insert an
extra advance" message.

NOTE: this fixture is a **negative-path** fixture — the JSON file
documents the inputs and expected ValidationError, not a solver output.
Sibling test `test_odd_first_period_too_long_raises` is added.

### Task 4 — Ship `regz_appendix_j_unit_period_monthly_regular.json`

Wikipedia anchor exactly: $200k @ 6.5% / 30yr / $1264.14 monthly. No
finance charges, no odd period. Expected APR == nominal `0.065000`
within Decimal("0.00001").

```json
{
  "description": "Wikipedia $200k @ 6.5%/30yr regular monthly — sanity: APR == nominal rate.",
  "citation": "Phase 1 oracle anchor + Reg Z Appendix J §(b)(1) regular case",
  "request": {
    "loan": {
      "principal": "200000.00",
      "annual_rate": "0.065000",
      "term_months": 360,
      "loan_type": "fixed"
    },
    "finance_charges": "0.00",
    "advance_schedule": [{"unit_period_offset": 0, "amount": "200000.00"}],
    "payment_schedule": [{"starting_unit_period": 1, "periods": 360, "amount": "1264.14"}],
    "day_count": "30/360",
    "unit_periods_per_year": 12,
    "odd_first_period_days": 0
  },
  "expected": {
    "estimated_apr": "0.065000",
    "iterations_max": 3,
    "tolerance_used": "0.00001",
    "note": "Regular monthly mortgage with no finance charges — APR == nominal rate exactly."
  }
}
```

### Task 5 — Flip Wave 0 stubs

Replace `pytest.fail("Wave 0 stub")` and remove `@pytest.mark.xfail`:

```python
def test_apr_reg_z_appendix_j_worked_example_returns_12_percent(
    apr_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """APR-05 + ROADMAP SC-1: $5000 / 36 / $166.07 → APR == 12.00% within Decimal('0.00001')."""
    from lib.apr import APRRequest, solve_apr
    fix = apr_fixture("regz_appendix_j_5000_36_166_07")
    request = APRRequest.model_validate(fix["request"])
    response = solve_apr(request)
    expected = Decimal(fix["expected"]["estimated_apr"])
    diff = abs(response.estimated_apr - expected)
    assert diff <= Decimal("0.00001"), \
        f"SC-1: APR must equal {expected} within Decimal('0.00001'); got {response.estimated_apr} (diff {diff})"


def test_newton_raphson_iterations_under_50_for_all_fixtures(
    apr_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """ROADMAP SC-3: every Phase 7 hand-calc fixture converges in <=50 Newton iterations."""
    from lib.apr import APRRequest, solve_apr
    stems = [
        "regz_appendix_j_5000_36_166_07",
        "regz_appendix_j_odd_first_period_15_days",
        "regz_appendix_j_unit_period_monthly_regular",
    ]
    for stem in stems:
        fix = apr_fixture(stem)
        request = APRRequest.model_validate(fix["request"])
        response = solve_apr(request)
        assert response.iterations <= 50, \
            f"SC-3: fixture {stem} converged in {response.iterations} iterations (cap=50)"
```

### Task 6 — Add parametric per-fixture coverage

```python
@pytest.mark.parametrize("stem,expected_apr", [
    ("regz_appendix_j_5000_36_166_07", Decimal("0.120000")),
    ("regz_appendix_j_unit_period_monthly_regular", Decimal("0.065000")),
])
def test_apr_hand_calc_fixtures_match_expected(
    apr_fixture: Callable[[str], dict[str, Any]],
    stem: str,
    expected_apr: Decimal,
) -> None:
    """Per-fixture parametric coverage of hand-calc anchors."""
    from lib.apr import APRRequest, solve_apr
    request = APRRequest.model_validate(apr_fixture(stem)["request"])
    response = solve_apr(request)
    assert abs(response.estimated_apr - expected_apr) <= Decimal("0.00001")
```

### Task 7 — Add `_decimal_pow` sanity test (Wave 2 D-13 pin)

```python
def test_decimal_pow_fractional_exponent_correctness() -> None:
    """D-13 sanity: _decimal_pow(2, 0.5) ≈ sqrt(2) within Decimal('0.0000001')."""
    from lib.apr import _decimal_pow
    result = _decimal_pow(Decimal("2"), Decimal("0.5"))
    expected = Decimal("1.41421356")
    assert abs(result - expected) <= Decimal("0.0000001")
```

## Acceptance

- All 4 fixture files exist + valid JSON
- `pytest tests/test_apr.py::test_apr_reg_z_appendix_j_worked_example_returns_12_percent -v` PASSES
- `pytest tests/test_apr.py::test_newton_raphson_iterations_under_50_for_all_fixtures -v` PASSES
- `pytest tests/test_apr.py::test_apr_hand_calc_fixtures_match_expected -v` PASSES (2 cases)
- `pytest tests/test_apr.py::test_decimal_pow_fractional_exponent_correctness -v` PASSES
- After this wave: 11 of 13 Wave 0 stubs flipped (APR-04 stays xfail until Wave 7; APR-08 stays xfail until Wave 6)
- `pytest -q 2>&1 | tail -5` shows ≥432 + 11 passed + 2 xfailed

## LOCKED DECISIONS

- **D-23:** Fixture file format = `{description, citation, request, expected}`. Mirrors Phase 4 / Phase 5 fixture convention (Phase 4 04-06).
- **D-24:** `expected.estimated_apr` for hand-calc fixtures is the engine-emitted value pinned at first compute (Phase 4 04-06 + Phase 3 D-04 idiom: avoids hand-calc rounding differences).
- **D-25:** SC-1 anchor expected value is the regulatory `0.120000` (12.00%), NOT engine-emitted — this is the Reg Z Example J-1 published value and the engine MUST agree with it. If engine disagrees, that is a P0 release blocker pinned by SC-1.
- **D-26:** Long odd first period (>= 1 unit period) test is a NEGATIVE-path test asserting ValueError; do NOT attempt to compute APR for that fixture.
- **D-27:** Parametric coverage shipped initially with 2 cases; Wave 7 extends with all 20+ FFIEC captures via a separate parametric test (different test function, mirrors Phase 5 oracle vs hand-calc test split).

## Verify Block

```bash
cd /Users/cujo253/Documents/mortgage-ops
ls tests/fixtures/apr/*.json
pytest tests/test_apr.py -v --tb=short 2>&1 | tail -30
mypy --strict tests/test_apr.py
ruff check tests/test_apr.py
ruff format --check tests/test_apr.py
pytest -q 2>&1 | tail -5
```

## Deviation Rules

- Rule-1: SC-1 anchor MUST converge to `Decimal("0.120000")` exactly. Any
  deviation indicates an engine bug — STOP and investigate before adjusting
  fixture or tolerance.
- Rule-2: hand-verify the 15-day odd-period APR via the U-equation by
  hand on a calculator before pinning the engine output.
- Rule-3: hygiene only.

## Cross-wave Dependency Notes

- **Upstream:** Waves 0-4 (test infra + models + solver + odd-period helper + CLI).
- **Downstream:** Wave 6 (references doc) cites these fixtures as the
  worked-example references; Wave 7 (FFIEC) extends the parametric
  coverage with the 20+ oracle corpus.
- APR-05 fully closed by this wave.
