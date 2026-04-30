---
phase: 04-affordability
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/conftest.py
  - tests/fixtures/affordability/.gitkeep
  - tests/test_affordability.py
autonomous: true
requirements: [AFFD-01, AFFD-02, AFFD-03, AFFD-04, AFFD-05, AFFD-06, AFFD-07, AFFD-08, AFFD-09]
requirements_addressed: [AFFD-01, AFFD-02, AFFD-03, AFFD-04, AFFD-05, AFFD-06, AFFD-07, AFFD-08, AFFD-09]
tags: [phase-4, affordability, test-infrastructure, wave-0]

must_haves:
  truths:
    - "tests/conftest.py exposes an `affordability_fixture` factory mirroring `amortize_fixture` (D-17)"
    - "tests/fixtures/affordability/ exists as a committed directory (D-17)"
    - "tests/test_affordability.py exists with a stub for every AFFD-01..09 requirement (Wave 0 stub seeds)"
    - "Stub-presence baseline test passes: pytest collects all 9 stubs; each marked as xfail or skip with reason `Wave 1+ implementation pending`"
    - "FIXTURE_DIR / 'affordability' subpath is referenced in conftest.py (extends Phase 1 FIXTURE_DIR pattern)"
    - "Subprocess SCRIPT_PATH = .../scripts/affordability.py constant is wired (Phase 3 D-17 portability discipline)"
  artifacts:
    - path: tests/conftest.py
      provides: "affordability_fixture pytest fixture factory"
      contains: "def affordability_fixture"
    - path: tests/fixtures/affordability/.gitkeep
      provides: "committed empty fixtures directory"
    - path: tests/test_affordability.py
      provides: "test module skeleton with one stub per AFFD-XX requirement"
      contains: "def test_AFFD_01"
      min_lines: 60
  key_links:
    - from: tests/conftest.py
      to: tests/fixtures/affordability/
      via: "FIXTURE_DIR / 'affordability' / f'{stem}.json' path construction"
      pattern: "FIXTURE_DIR / .affordability."
    - from: tests/test_affordability.py
      to: scripts/affordability.py
      via: "SCRIPT_PATH constant pointing at project-root scripts/affordability.py (Phase 3 D-17 mirror)"
      pattern: "SCRIPT_PATH.*scripts.*affordability\\.py"
---

<objective>
Build the Wave 0 test scaffolding for Phase 4 BEFORE any production code exists. Per Phase 4 VALIDATION.md, this plan satisfies the Nyquist-compliant "Wave 0 covers all MISSING references" gate so subsequent waves' tasks can express `<verify><automated>pytest tests/test_affordability.py::<stub_name> -x</automated></verify>` against real test files.

Purpose: enable per-task feedback sampling (max latency 20s) for every Wave 1+ task, in advance of any `lib/affordability.py` or `scripts/affordability.py` source. Without this scaffold, Wave 1+ tasks cannot satisfy the planner's automated-verify requirement and would have to ship as Rule-1 deviations.

Output:
- `tests/conftest.py` extended with `affordability_fixture` factory (mirrors Phase 3's `amortize_fixture`)
- `tests/fixtures/affordability/` committed as an empty directory (`.gitkeep`)
- `tests/test_affordability.py` skeleton: imports + AFFD-01..09 xfail stubs + SCRIPT_PATH constant + AFFORDABILITY_MODULE_PATH constant

Decisions implemented: D-17 (fixture loader pattern), D-13 (SCRIPT_PATH portability for Phase 10 relocation).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-affordability/04-CONTEXT.md
@.planning/phases/04-affordability/04-RESEARCH.md
@.planning/phases/04-affordability/04-PATTERNS.md
@.planning/phases/04-affordability/04-VALIDATION.md
@CLAUDE.md
@tests/conftest.py
@tests/test_amortize.py

<interfaces>
<!-- Existing tests/conftest.py exports (extracted from source). Wave 0 mirrors these. -->
<!-- Loader signature contract — match this exactly. -->

From tests/conftest.py:
```python
FIXTURE_DIR: Path = Path(__file__).parent / "fixtures"

@pytest.fixture
def golden_fixture() -> Callable[[str], dict[str, Any]]:
    # loads from FIXTURE_DIR / "golden_pmt.json" (array shape, fixture_id keyed)
    ...

@pytest.fixture
def amortize_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads a single amortize fixture by filename stem
    from tests/fixtures/amortize/. Raises FileNotFoundError if the stem doesn't exist.
    [...] Loader takes a filename stem like "biweekly_true_200k_6_5", not a fixture
    id within an array.
    """
    def _load(stem: str) -> dict[str, Any]:
        path = FIXTURE_DIR / "amortize" / f"{stem}.json"
        return json.loads(path.read_text())
    return _load
```

From tests/test_amortize.py:
```python
AMORTIZE_MODULE_PATH: Path = Path(__file__).resolve().parent.parent / "lib" / "amortize.py"
SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "amortize.py"
"""Phase 3 CLI lives at project root scripts/. Phase 10 will relocate to
.claude/skills/mortgage-ops/scripts/; only this constant updates."""
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend tests/conftest.py with affordability_fixture factory</name>
  <files>tests/conftest.py</files>
  <read_first>
    - tests/conftest.py (current state — must NOT remove existing fixtures)
    - .planning/phases/04-affordability/04-PATTERNS.md §"tests/conftest.py (MODIFY ...)"
    - .planning/phases/04-affordability/04-CONTEXT.md D-17 (fixture loader pattern locked)
  </read_first>
  <action>
    Append (do NOT replace) a sibling `affordability_fixture` factory to `tests/conftest.py`. Pattern is exact-mirror of `amortize_fixture` at lines 38-52, verbatim per PATTERNS §"Phase 4 adaptation — append a sibling factory":

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

    Place it AFTER the existing `amortize_fixture` definition (preserves Phase 1 + Phase 3 ordering). Do NOT modify FIXTURE_DIR (line 19) or any existing fixture.

    Per D-17, this is the canonical loader pattern. Per Phase 1 / Phase 3 discretion convention: extend, don't invent.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run python -c "from tests.conftest import *; import tests.conftest as c; assert hasattr(c, 'affordability_fixture'), 'affordability_fixture not exported'; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - tests/conftest.py contains literal substring `def affordability_fixture(` (factory function defined)
    - tests/conftest.py contains literal substring `FIXTURE_DIR / "affordability" / f"{stem}.json"` (path construction matches Phase 3 idiom)
    - tests/conftest.py still contains literal substring `def amortize_fixture(` (Phase 3 fixture preserved)
    - tests/conftest.py still contains literal substring `def golden_fixture(` (Phase 1 fixture preserved)
    - `grep -c "FIXTURE_DIR" tests/conftest.py | grep -v '^#'` returns &gt;= 3 (golden + amortize + affordability path constructions)
    - `uv run pytest --collect-only tests/conftest.py 2>&amp;1 | grep -c "error"` returns 0 (collection clean)
  </acceptance_criteria>
  <done>
    affordability_fixture is registered as a pytest fixture (hasattr check passes); FIXTURE_DIR + Phase 1/3 fixtures untouched; collection has zero errors.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create tests/fixtures/affordability/ with .gitkeep</name>
  <files>tests/fixtures/affordability/.gitkeep</files>
  <read_first>
    - .planning/phases/04-affordability/04-CONTEXT.md D-17 (fixture directory locked)
    - .planning/phases/04-affordability/04-VALIDATION.md §"Wave 0 Requirements"
  </read_first>
  <action>
    Create `tests/fixtures/affordability/` directory by writing an empty `.gitkeep` file at `tests/fixtures/affordability/.gitkeep`. This commits the directory so the affordability_fixture loader does not raise FileNotFoundError on the directory itself when Wave 3 fixtures land.

    The `.gitkeep` file is a 0-byte sentinel; convention recognized by all Git workflows. Wave 3 (Plan 04-06) populates it with the 9+ fixture JSONs from D-17.
  </action>
  <verify>
    <automated>test -d /Users/cujo253/Documents/mortgage-ops/tests/fixtures/affordability &amp;&amp; test -f /Users/cujo253/Documents/mortgage-ops/tests/fixtures/affordability/.gitkeep &amp;&amp; echo OK</automated>
  </verify>
  <acceptance_criteria>
    - `tests/fixtures/affordability/` exists as a directory
    - `tests/fixtures/affordability/.gitkeep` exists as a file (0-byte OK)
    - `git status --porcelain tests/fixtures/affordability/.gitkeep` shows the file is staged or modified (will be committed by orchestrator)
  </acceptance_criteria>
  <done>
    Empty fixtures directory committed via .gitkeep sentinel; ready for Wave 3 fixture population.
  </done>
</task>

<task type="auto">
  <name>Task 3: Create tests/test_affordability.py skeleton with AFFD-01..09 stubs</name>
  <files>tests/test_affordability.py</files>
  <read_first>
    - tests/test_amortize.py (lines 1-60 for imports + SCRIPT_PATH constant pattern)
    - .planning/phases/04-affordability/04-PATTERNS.md §"tests/test_affordability.py (unit + integration tests)"
    - .planning/phases/04-affordability/04-CONTEXT.md (full file — every D-XX referenced in stubs)
    - .planning/phases/04-affordability/04-RESEARCH.md §"Phase Requirements → Test Map"
  </read_first>
  <action>
    Create `tests/test_affordability.py` as a Wave 0 skeleton with:

    **Module docstring (top of file):**
    ```python
    """Phase 4 Affordability — test surface (AFFD-01..09).

    Wave 0 stub: every AFFD-XX requirement has a stub function that pytest
    collects. Stubs are marked `pytest.mark.xfail(strict=False, reason="Wave N
    implementation pending")` so the suite stays green during Wave 1-3
    implementation. Each Wave 1+ task replaces its stub body with the real
    test (RED→GREEN flip).

    Per Phase 3 D-17 portability: subprocess invocation only, never
    `import scripts.affordability` directly. SCRIPT_PATH is the single
    constant edited at Phase 10 when scripts/ relocates to
    .claude/skills/mortgage-ops/scripts/.

    Per CONTEXT.md D-18: exact Decimal equality, never assertAlmostEqual or
    pytest.approx.

    Per RESEARCH §"Phase 2 Predicate Signature Audit": Phase 4 calls
    `loan_type.classify(loan_amount, county, program=...)`,
    `conventional_pmi.status(loan, scheduled_balance, original_property_value, ...)`,
    `fha_mip.compute(loan, original_property_value, endorsement_date)`. The
    CONTEXT.md D-02 signatures are CORRECTED in RESEARCH §A.1-A.3.
    """
    ```

    **Imports (mirror tests/test_amortize.py):**
    ```python
    from __future__ import annotations

    import json
    import subprocess
    import sys
    from decimal import Decimal
    from pathlib import Path
    from typing import TYPE_CHECKING, Any

    import pytest

    if TYPE_CHECKING:
        from collections.abc import Callable
    ```

    **Constants (mirror tests/test_amortize.py:50-53):**
    ```python
    AFFORDABILITY_MODULE_PATH: Path = (
        Path(__file__).resolve().parent.parent / "lib" / "affordability.py"
    )
    SCRIPT_PATH: Path = (
        Path(__file__).resolve().parent.parent / "scripts" / "affordability.py"
    )
    """Phase 4 CLI lives at project-root scripts/. Phase 10 will relocate to
    .claude/skills/mortgage-ops/scripts/; only this constant updates."""
    ```

    **Stubs (one per AFFD-XX, ALL marked xfail with structured reason):**
    ```python
    @pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-01 implementation pending (Plan 04-02)")
    def test_AFFD_01_dti_calculations() -> None:
        """AFFD-01: DTI front-end + back-end exact Decimal (per RESEARCH Test Map).

        Wave 1+ replaces this body with real assertions against
        lib.affordability.evaluate_forward(...).
        """
        raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-02")


    @pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-02 implementation pending (Plan 04-02)")
    def test_AFFD_02_ltv_calculation() -> None:
        """AFFD-02: LTV = loan_amount / property_value (per RESEARCH §LTV/CLTV)."""
        raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-02")


    @pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-03 implementation pending (Plan 04-02)")
    def test_AFFD_03_cltv_with_junior_liens() -> None:
        """AFFD-03: CLTV = (loan_amount + sum(junior_liens)) / property_value (D-discretion: list[Money])."""
        raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-02")


    @pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-04 implementation pending (Plan 04-02)")
    def test_AFFD_04_piti_composition() -> None:
        """AFFD-04: PITI = quantize_cents(P&I + tax + ins + HOA + MI) (D-01 caller-supplied escrow; D-02 predicate-derived MI; quantize ONCE end-of-period)."""
        raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-02")


    @pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-05 implementation pending (Plan 04-03)")
    def test_AFFD_05_reverse_round_trip() -> None:
        """AFFD-05 + SC-2: npf.pv reverse + round-trip closure within Decimal('0.0001') (D-08 + D-09)."""
        raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-03")


    @pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-06 implementation pending (Plan 04-02)")
    def test_AFFD_06_joint_applicants() -> None:
        """AFFD-06 + SC-5: sum(income) + min(credit_score) across applicants (D-05 + D-06)."""
        raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-02")


    @pytest.mark.xfail(strict=False, reason="Wave 1: AFFD-07 implementation pending (Plan 04-04)")
    def test_AFFD_07_blocked_by_va_residual_west_family_4() -> None:
        """AFFD-07 + SC-3: blocked_by == 'VA-RESIDUAL-WEST-FAMILY-4' verbatim (Phase 2 D-11 stable citation)."""
        raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-04")


    @pytest.mark.xfail(strict=False, reason="Wave 2: AFFD-08 implementation pending (Plan 04-05)")
    def test_AFFD_08_cli_smoke() -> None:
        """AFFD-08: scripts/affordability.py JSON-in/JSON-out subprocess smoke (D-13 + Phase 3 D-17/18/19)."""
        raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-05")


    @pytest.mark.xfail(strict=False, reason="Wave 3: AFFD-09 implementation pending (Plan 04-06)")
    def test_AFFD_09_household_example_yml_e2e() -> None:
        """AFFD-09 + SC-4: config/household.example.yml end-to-end via subprocess (D-15 + D-17 fixture)."""
        raise NotImplementedError("Wave 0 stub — implementation comes in Plan 04-06")
    ```

    NO production-code imports yet (lib.affordability does not exist; importing it would fail collection — only Plan 04-01 creates it). Stubs raise NotImplementedError inside the function body so xfail catches them at test-execution time, not collection time.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run pytest tests/test_affordability.py --collect-only -q 2>&amp;1 | grep -c "test_AFFD_0"</automated>
  </verify>
  <acceptance_criteria>
    - tests/test_affordability.py contains literal substring `AFFORDABILITY_MODULE_PATH: Path = (`
    - tests/test_affordability.py contains literal substring `SCRIPT_PATH: Path = (`
    - tests/test_affordability.py contains literal substring `"affordability.py"` (script path string, single source for Phase 10 relocation)
    - tests/test_affordability.py contains literal substring `def test_AFFD_01_dti_calculations`
    - tests/test_affordability.py contains literal substring `def test_AFFD_02_ltv_calculation`
    - tests/test_affordability.py contains literal substring `def test_AFFD_03_cltv_with_junior_liens`
    - tests/test_affordability.py contains literal substring `def test_AFFD_04_piti_composition`
    - tests/test_affordability.py contains literal substring `def test_AFFD_05_reverse_round_trip`
    - tests/test_affordability.py contains literal substring `def test_AFFD_06_joint_applicants`
    - tests/test_affordability.py contains literal substring `def test_AFFD_07_blocked_by_va_residual_west_family_4`
    - tests/test_affordability.py contains literal substring `def test_AFFD_08_cli_smoke`
    - tests/test_affordability.py contains literal substring `def test_AFFD_09_household_example_yml_e2e`
    - `grep -c "@pytest.mark.xfail" tests/test_affordability.py | grep -v '^#'` returns 9 (one per AFFD requirement)
    - `uv run pytest tests/test_affordability.py -x --tb=short` exits 0 (xfail does NOT fail; xpassed if a stub mistakenly passes)
    - `uv run pytest tests/test_affordability.py --collect-only -q | grep -c "::test_AFFD_0"` returns 9
    - tests/test_affordability.py does NOT contain literal substring `from lib.affordability` (Wave 0 — module does not exist yet)
    - tests/test_affordability.py does NOT contain literal substring `assertAlmostEqual` (D-18 enforcement)
    - tests/test_affordability.py does NOT contain literal substring `pytest.approx` (D-18 enforcement)
  </acceptance_criteria>
  <done>
    9 xfail stubs collect cleanly; module skeleton imports work; SCRIPT_PATH + AFFORDABILITY_MODULE_PATH constants point at the correct Phase 10 relocation seam; full suite stays green.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pytest collection → test files | Untrusted test files could be planted to skip enforcement; mitigated by file-ownership in this plan + git diff review |
| FIXTURE_DIR path resolution | `Path(__file__).parent / "fixtures"` is hard-coded relative to conftest.py — no user input |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-00-01 | Tampering | tests/conftest.py affordability_fixture | mitigate | Sibling-pattern matches existing amortize_fixture exactly; grep gates pin path construction string `FIXTURE_DIR / "affordability" / f"{stem}.json"` so a path-traversal-style modification to load arbitrary YAMLs would fail acceptance. |
| T-04-00-02 | Repudiation | tests/test_affordability.py xfail stubs | accept | Each stub has a structured `reason="Wave N: AFFD-XX implementation pending (Plan 04-NN)"` so a test silently dropped from the suite later (in Wave 1+) is detectable via grep audit (`grep -c "Wave .: AFFD"` should drop by exactly 1 per Wave-N task). Low risk; visible in PR diff. |
| T-04-00-03 | Information Disclosure | tests/fixtures/affordability/.gitkeep | accept | Empty 0-byte sentinel; no PII surface; pre-commit hook on User-Layer files (FND-04) does not match `.gitkeep`. |
| T-04-00-04 | Tampering | Pre-commit hook bypass on User Layer | mitigate | This plan does NOT modify any User-Layer file (`config/household.yml`, `config/profile.yml`); the FND-04 pre-commit hook should NOT fire. If it does, plan author has accidentally targeted a User-Layer path — reject the commit. |
</threat_model>

<verification>
After all 3 tasks complete, run the full Phase 4 Wave 0 acceptance gate:

```bash
# Files exist
test -f tests/conftest.py
test -d tests/fixtures/affordability
test -f tests/fixtures/affordability/.gitkeep
test -f tests/test_affordability.py

# affordability_fixture is registered
uv run python -c "from tests.conftest import *; import tests.conftest as c; assert hasattr(c, 'affordability_fixture'); print('OK')"

# 9 stubs collect
[ "$(uv run pytest tests/test_affordability.py --collect-only -q 2>/dev/null | grep -c '::test_AFFD_0')" = "9" ]

# Stubs all xfail (suite stays green; Wave 1+ flips RED→GREEN per stub)
uv run pytest tests/test_affordability.py -x --tb=short

# Full project suite still green (Phase 1/2/3 unaffected)
uv run pytest -x

# mypy strict still clean (no new untyped code)
uv run mypy --strict tests/conftest.py tests/test_affordability.py

# ruff still clean
uv run ruff check tests/conftest.py tests/test_affordability.py
```
</verification>

<success_criteria>
- [ ] `tests/conftest.py` extended with `affordability_fixture` mirroring Phase 3's `amortize_fixture` (D-17)
- [ ] `tests/fixtures/affordability/` directory created with `.gitkeep` (Wave 3 fixture-population scaffold)
- [ ] `tests/test_affordability.py` exists with 9 xfail stubs (one per AFFD-01..09)
- [ ] SCRIPT_PATH + AFFORDABILITY_MODULE_PATH constants pin Phase 10 relocation seam
- [ ] No D-18 violations: zero occurrences of `assertAlmostEqual` or `pytest.approx`
- [ ] Full project suite still green (no regressions to Phase 1/2/3 tests)
- [ ] mypy --strict + ruff clean on the 2 modified test files
- [ ] Plans 04-01 through 04-06 can each express `<verify><automated>pytest tests/test_affordability.py::test_AFFD_NN_xxx -x</automated></verify>` (Nyquist-compliant gate enabled)
</success_criteria>

<output>
After completion, create `.planning/phases/04-affordability/04-00-SUMMARY.md` per the standard template.

Note for orchestrator: this plan is Wave 0; Plans 04-01..04-04 (Wave 1) MUST NOT start until this plan is committed. Plan 04-05 (Wave 2) and Plan 04-06 (Wave 3) follow per the wave structure.
</output>
