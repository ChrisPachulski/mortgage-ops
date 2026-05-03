---
phase: 07
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/conftest.py
  - tests/test_apr.py
  - tests/fixtures/apr/.gitkeep
  - tests/fixtures/apr/oracle/.gitkeep
autonomous: true
requirements: []
tags:
  - phase-07
  - estimated-apr
  - test-infrastructure
  - nyquist
must_haves:
  truths:
    - "tests/test_apr.py file exists and is collected by pytest"
    - "Every Phase 7 requirement (APR-01..08) + 5 cross-cutting tests have an xfail-decorated stub"
    - "Stub file runs (pytest tests/test_apr.py -v) without ImportError; xfail tests show as XFAIL not ERROR"
    - "tests/conftest.py exposes apr_fixture pytest fixture loadable by name from any test"
    - "tests/fixtures/apr/ and tests/fixtures/apr/oracle/ directories are committed (via .gitkeep)"
    - "Phase 7 test scaffold is additive — no behavior change to Phase 1-5 production code or existing tests"
  artifacts:
    - path: "tests/test_apr.py"
      provides: "13 xfail stubs covering APR-01..08 + cross-cutting (Newton iteration cap, lazy-import, float-gate, envelope uniformity, non-convergence)"
      min_lines: 200
    - path: "tests/conftest.py"
      provides: "apr_fixture loader (parallel to amortize/affordability/arm fixtures)"
      contains: "def apr_fixture"
    - path: "tests/fixtures/apr/.gitkeep"
      provides: "Empty placeholder to commit hand-calc fixture directory"
    - path: "tests/fixtures/apr/oracle/.gitkeep"
      provides: "Empty placeholder to commit FFIEC oracle capture directory"
  key_links:
    - from: "tests/test_apr.py"
      to: "tests/conftest.py"
      via: "apr_fixture parametric injection"
      pattern: "def test_.*\\(.*apr_fixture"
    - from: "Wave 1-7 plans"
      to: "tests/test_apr.py xfail decorators"
      via: "incremental flip from xfail → pass as engine slices land"
      pattern: "@pytest.mark.xfail"
---

## Goal

Establish Phase 7 test scaffolding (Nyquist gate). Ship `apr_fixture`
pytest loader, 13 xfail stubs covering APR-01..08 + 5 cross-cutting
contracts, and the empty `tests/fixtures/apr/` + `tests/fixtures/apr/oracle/`
directories. Subsequent waves flip the xfails as the engine, CLI, fixtures,
and references doc land.

## Tasks

### Task 1 — Extend `tests/conftest.py` with `apr_fixture` loader

Append (after `arm_fixture` at line 90):

```python


@pytest.fixture
def apr_fixture() -> Callable[[str], dict[str, Any]]:
    """Loads APR fixtures by filename stem from tests/fixtures/apr/.

    Mirrors arm_fixture: one-fixture-per-file shape; loader takes a
    stem like "regz_appendix_j_5000_36_166_07". FFIEC oracle captures
    live at tests/fixtures/apr/oracle/; callers pass
    "oracle/ffiec_001_30yr_400k_6_5" as the stem to load those.
    """
    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "apr" / f"{stem}.json"
        return json.loads(path.read_text())  # type: ignore[no-any-return]
    return _load
```

Do NOT modify any existing fixture function.

### Task 2 — Create `tests/fixtures/apr/.gitkeep` + `tests/fixtures/apr/oracle/.gitkeep`

Two empty (zero-byte) files via Write tool with empty string content.

### Task 3 — Create `tests/test_apr.py` with 13 xfail stubs

File structure (mirror `tests/test_arm.py:1-300`):

```python
"""Phase 7 Estimated APR — full test surface (APR-01..08 + cross-cutting).

Per Phase 3 D-17 portability + Phase 4 D-13 inheritance: subprocess
invocation only for CLI tests, never `import scripts.apr_reg_z`
directly.

Wave 0 (Plan 07-00) creates ALL 13 tests as xfail stubs. Subsequent waves
flip the relevant xfail decorators to real assertions:

- Wave 1 (Plan 07-01 Pydantic models): APR-01 partial (1 stub)
- Wave 2 (Plan 07-02 Newton-Raphson engine): APR-01 + APR-02 + APR-03 + non-conv (4 stubs)
- Wave 3 (Plan 07-03 odd-first-period helpers): rolled into Wave 5 fixture flips
- Wave 4 (Plan 07-04 CLI): APR-06 + APR-07 + 3 CLI cross-cutting (5 stubs)
- Wave 5 (Plan 07-05 tests + Reg Z anchor): APR-05 + iteration-cap (2 stubs)
- Wave 6 (Plan 07-06 references doc): APR-08 (1 stub)
- Wave 7 (Plan 07-07 FFIEC fixtures): APR-04 (1 stub)
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

if TYPE_CHECKING:
    from collections.abc import Callable

SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "apr_reg_z.py"
APR_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "apr.py"


# =========================================================================
# APR-01 (1 stub) — flipped in Wave 1 + 2
# =========================================================================

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-01 ships APRRequest; Plan 07-02 ships solve_apr")
def test_apr_solver_module_exists_with_newton_raphson_signature() -> None:
    """APR-01: lib/apr.py exposes solve_apr(APRRequest) -> APRResponse using Newton-Raphson."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-02 (1 stub) — flipped in Wave 2
# =========================================================================

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-02 ships npf.rate seed")
def test_apr_solver_seeded_from_npf_rate(apr_fixture: Callable[[str], dict[str, Any]]) -> None:
    """APR-02: First Newton iterate is exactly Decimal(str(npf.rate(n, -pmt, pv, 0)))."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-03 (1 stub) — flipped in Wave 2
# =========================================================================

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-02 ships convergence test")
def test_apr_solver_converges_within_decimal_00001_tolerance(apr_fixture: Callable[[str], dict[str, Any]]) -> None:
    """APR-03 + ROADMAP SC-1: |estimated_apr - expected| <= Decimal('0.00001') for the Reg Z anchor."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-04 (1 stub) — flipped in Wave 7 (FFIEC capture human checkpoint)
# =========================================================================

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-07 ships 20+ FFIEC fixtures")
def test_apr_ffiec_oracle_fixtures_match_within_decimal_00001(apr_fixture: Callable[[str], dict[str, Any]]) -> None:
    """APR-04 + ROADMAP SC-2: All 20+ FFIEC captures pass within Decimal('0.00001')."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-05 (1 stub) — flipped in Wave 5
# =========================================================================

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-05 ships regz_appendix_j_5000_36_166_07.json")
def test_apr_reg_z_appendix_j_worked_example_returns_12_percent(apr_fixture: Callable[[str], dict[str, Any]]) -> None:
    """APR-05 + ROADMAP SC-1: $5000 / 36 monthly $166.07 → APR == 12.00% within Decimal('0.00001')."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-06 (1 stub) — flipped in Wave 4
# =========================================================================

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-04 ships APRResponse.summary literal-text contract")
def test_apr_response_uses_literal_estimated_apr_text(apr_fixture: Callable[[str], dict[str, Any]]) -> None:
    """APR-06 + ROADMAP SC-4: APRResponse.summary contains literal 'estimated APR'; never bare 'APR'."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-07 (1 stub) — flipped in Wave 4
# =========================================================================

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-04 ships scripts/apr_reg_z.py")
def test_apr_cli_subprocess_round_trip(apr_fixture: Callable[[str], dict[str, Any]], tmp_path: Path) -> None:
    """APR-07: CLI subprocess round-trip — write JSON, invoke, parse stdout."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# APR-08 (1 stub) — flipped in Wave 6
# =========================================================================

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-06 ships references/apr-reg-z.md")
def test_references_apr_reg_z_doc_present_with_required_sections() -> None:
    """APR-08 + ROADMAP SC-5: references/apr-reg-z.md exists with §1-6 (unit-period, day-count, odd-first, worked example, Newton, citations)."""
    pytest.fail("Wave 0 stub")


# =========================================================================
# Cross-cutting (5 stubs)
# =========================================================================

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-02 + 07-05 enforce SC-3 iteration cap")
def test_newton_raphson_iterations_under_50_for_all_fixtures(apr_fixture: Callable[[str], dict[str, Any]]) -> None:
    """ROADMAP SC-3: every fixture (anchor + 20 FFIEC) converges in <=50 Newton iterations."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-04 ships lazy-import in scripts/apr_reg_z.py")
def test_apr_cli_help_does_not_import_lib_apr() -> None:
    """D-18 inheritance: --help fast (no lib.apr or numpy_financial import before argparse)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-04 ships float-gate")
def test_apr_cli_rejects_float_loan_amount(tmp_path: Path) -> None:
    """D-19 + WR-02 inheritance: CLI rejects JSON-float in loan.principal with 6-key envelope."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-04 ships uniform envelope")
def test_apr_cli_error_envelope_uniformity(tmp_path: Path) -> None:
    """WR-02 inheritance: float-gate + Pydantic ValidationError emit identical 6-key shape."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 07-02 ships APRConvergenceError")
def test_apr_solver_raises_on_non_convergence() -> None:
    """Phase 7 contract: ill-conditioned input → APRConvergenceError(iterations, last_residual) after 50 caps."""
    pytest.fail("Wave 0 stub")
```

### Task 4 — Verify zero regression to Phase 5 baseline + commit Wave 0

Run full suite. Expected: ≥432 passed (Phase 5 baseline) + 13 xfailed (Phase 7
new) + 0 failed + 0 errors.

`mypy --strict tests/conftest.py tests/test_apr.py`
`ruff check tests/conftest.py tests/test_apr.py`
`ruff format --check tests/conftest.py tests/test_apr.py`

## Acceptance

- `grep -c '@pytest.mark.xfail(strict=True' tests/test_apr.py` returns 13
- `grep -c 'def test_' tests/test_apr.py` returns 13
- All 13 named test functions present (one grep per name in Task 3 list)
- `pytest tests/test_apr.py -v --tb=no 2>&1 | grep -c XFAIL` returns 13
- `pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ passed'` shows ≥432
- `mypy --strict` + `ruff check` + `ruff format --check` all clean

## LOCKED DECISIONS

- **D-00-01:** Test inventory pinned at 13 stubs (8 requirement-mapped + 5
  cross-cutting). Adding stubs requires plan revision. Mirrors Phase 5
  D-09 (32 ARM stubs locked at Wave 0).
- **D-00-02:** All xfail decorators use `strict=True`. An accidental pass
  raises XPASS, forcing the wave that fixes the test to also remove the
  decorator (mirrors Phase 5 D-09).
- **D-00-03:** `apr_fixture` loader path is `FIXTURE_DIR / "apr" / f"{stem}.json"`
  (no shape transformations; raw JSON dict). Mirrors `arm_fixture`.

## Verify Block

```bash
cd /Users/cujo253/Documents/mortgage-ops
pytest tests/test_apr.py -v --tb=no 2>&1 | tail -30
pytest -q 2>&1 | tail -10
mypy --strict tests/conftest.py tests/test_apr.py
ruff check tests/conftest.py tests/test_apr.py
ruff format --check tests/conftest.py tests/test_apr.py
```

## Deviation Rules

- Rule-1 (test-name drift): if any of the 13 stub names changes during
  execution, the change MUST propagate to subsequent wave plans (each
  wave references the names verbatim).
- Rule-3 (hygiene only): mypy/ruff fixes that do not change tests are
  allowed inline; document in SUMMARY.

## Cross-wave Dependency Notes

- **Downstream:** Waves 1-7 each flip a known subset of these stubs.
  Wave 7 (FFIEC capture) is a human checkpoint — if it cannot complete,
  the APR-04 stub remains xfail and the phase ships with documented
  partial closure (mirrors Phase 5 ARM-06 partial — Phase 5 deferred 5/1
  cross-source to Phase 8).
