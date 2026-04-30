---
phase: 05
plan: 01
type: execute
wave: 1
depends_on:
  - "05-00"
files_modified:
  - lib/money.py
  - lib/affordability.py
  - tests/test_money.py
autonomous: true
requirements: []
tags:
  - phase-05
  - arm-modeling
  - quantize-rate
  - d-14-promotion
  - hygiene-factor
must_haves:
  truths:
    - "lib.money exposes a public function quantize_rate(Decimal) -> Decimal that returns a 6-decimal-place ROUND_HALF_UP-rounded Decimal under MONEY_CONTEXT"
    - "lib/affordability.py no longer defines _quantize_rate (the local def is removed); all 4 prior call sites resolve to the public lib.money.quantize_rate via import"
    - "Phase 4 test suite (tests/test_affordability.py) still passes 379 + 4 (zero regression)"
    - "Phase 3 test suite (tests/test_amortize.py) still passes (Phase 5 does not touch amortize.py)"
    - "tests/test_money.py has a golden-pin for quantize_rate at the half-up boundary"
    - "Wave 2 (Plan 05-02) and Wave 3 (Plan 05-03) can import quantize_rate from lib.money without touching lib.affordability"
  artifacts:
    - path: "lib/money.py"
      provides: "Public quantize_rate(Decimal) -> Decimal helper at 6 decimal places (companion to existing quantize_cents at 2 places)"
      contains: "def quantize_rate"
      min_lines: 60
    - path: "lib/affordability.py"
      provides: "Affordability evaluation engine; now imports quantize_rate from lib.money rather than defining locally"
      contains: "from lib.money import"
    - path: "tests/test_money.py"
      provides: "Golden-pin test for quantize_rate (new) plus existing quantize_cents tests"
      contains: "def test_quantize_rate"
  key_links:
    - from: "lib/arm.py (created in Wave 2)"
      to: "lib.money.quantize_rate"
      via: "import"
      pattern: "from lib.money import.*quantize_rate"
    - from: "lib/affordability.py"
      to: "lib.money.quantize_rate"
      via: "import (replacing local _quantize_rate def)"
      pattern: "from lib.money import.*quantize_rate"
---

<objective>
Promote Phase 4's private `_quantize_rate` helper from `lib/affordability.py` to a public `lib/money.py.quantize_rate(Decimal) -> Decimal` so Phase 5's `lib/arm.py` (and every future Phase 6+ consumer) imports it from the project's canonical money-discipline module rather than reaching into a private affordability symbol.

Implements **D-14 promotion path** (recommended in CONTEXT.md + RESEARCH §Q9). Verified by RESEARCH grep: `_quantize_rate` is currently the ONLY consumer (1 def + 4 calls in lib/affordability.py:613-627, 930, 931, 945, 946). Phase 5 IS the second consumer.

Purpose:
1. **Engine hygiene** — the helper belongs in `lib/money.py` next to `quantize_cents`; Phase 1 D-08 / Phase 3 discretion explicitly says "scope to file until the second consumer needs it; promote on consumer 2."
2. **Phase 4 frozen-surface preservation** — the public `evaluate(...)` API of lib.affordability does not change; the internal helper migration is a pure-internal refactor with byte-equivalent behavior.

Output: lib/money.py +18 lines (def + docstring + _RATE_QUANTUM constant); lib/affordability.py -18 lines + 4 call-site renames; tests/test_money.py +1 golden-pin test; full Phase 4 + Phase 3 suites still green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/05-arm-modeling/05-CONTEXT.md
@.planning/phases/05-arm-modeling/05-RESEARCH.md
@.planning/phases/05-arm-modeling/05-PATTERNS.md
@CLAUDE.md
@lib/money.py
@lib/affordability.py
@tests/test_money.py

<interfaces>
Existing lib/money.py exports (Phase 5 EXTENDS, does NOT modify these):

- CENT: Final[Decimal] = Decimal("0.01")
- MONEY_CONTEXT: Final[Context] = Context(prec=28, rounding=ROUND_HALF_UP)
- def to_money(s: str) -> Decimal
- def quantize_cents(d: Decimal) -> Decimal

Existing helper to PROMOTE (currently in lib/affordability.py:613-627). The full block to lift is:

- _RATE_QUANTUM: Final[Decimal] = Decimal("0.000001")
- def _quantize_rate(rate: Decimal) -> Decimal returning rate.quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP) under localcontext(MONEY_CONTEXT)

4 call sites in lib/affordability.py at lines 930, 931, 945, 946 (RESEARCH §Q9 grep run on 2026-04-30) plus the def at line 616.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add quantize_rate + _RATE_QUANTUM to lib/money.py</name>
  <files>lib/money.py</files>
  <read_first>
    - lib/money.py (full file, 46 lines) — preserve all existing exports verbatim
    - lib/affordability.py:613-627 — the 15-line block to lift verbatim (rename _quantize_rate to quantize_rate)
    - 05-RESEARCH.md §Q9 (lines 296-348) — promotion path details + companion docstring
    - 05-PATTERNS.md "Pattern 3: _quantize_rate helper (D-14 candidate for promotion)" section
  </read_first>
  <action>
    Append a new public `quantize_rate` function to lib/money.py, mirroring the existing `quantize_cents` style. Append AFTER the existing `quantize_cents` definition. Do NOT modify or remove existing symbols.

    Insertion content (literal Python; place at end of file):

    ```
    _RATE_QUANTUM: Final[Decimal] = Decimal("0.000001")
    """The quantum for end-of-period rate rounding (matches lib.models.Rate decimal_places=6).

    Companion to CENT (the quantum for quantize_cents at 2 decimal places).
    Phase 5 D-14 promotes this constant from lib/affordability.py:613 (Phase 4)
    to lib/money.py because Phase 5's ARM engine becomes the second consumer.
    """


    def quantize_rate(rate: Decimal) -> Decimal:
        """Quantize a fractional rate to 6 decimal places using ROUND_HALF_UP.

        Companion to quantize_cents (2 decimal places for Money). Use for any
        Rate-typed value at end-of-period; never quantize mid-calculation
        (Phase 1 PITFALLS, Phase 3 D-04, Phase 4 D-09 inherited).

        The 6-decimal quantum matches lib.models.Rate's
        Annotated[Decimal, Field(max_digits=7, decimal_places=6)] constraint.

        Promoted from lib/affordability.py._quantize_rate (Phase 4 D-09) to
        lib/money.py per Phase 5 D-14 because Phase 5 lib/arm.py is the
        second consumer.
        """
        with localcontext(MONEY_CONTEXT):
            return rate.quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP)
    ```

    Verify imports at top of file already include `Final` (`from typing import Final`); if missing, add it. Existing imports already include `localcontext`, `ROUND_HALF_UP`, `Decimal`.

    Do NOT remove or modify CENT, MONEY_CONTEXT, to_money, or quantize_cents.
  </action>
  <verify>
    <automated>python -c 'from lib.money import quantize_rate; from decimal import Decimal; assert quantize_rate(Decimal("0.0654995")) == Decimal("0.065500"); assert quantize_rate(Decimal("0.0654994")) == Decimal("0.065499"); print("OK")'</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'def quantize_rate' lib/money.py` returns 1
    - `grep -c '_RATE_QUANTUM' lib/money.py` returns at least 2 (definition plus use inside function body)
    - `grep -c 'def quantize_cents' lib/money.py` returns 1 (existing — preserved)
    - `grep -c 'def to_money' lib/money.py` returns 1 (existing — preserved)
    - `python -c 'from lib.money import quantize_rate, quantize_cents, to_money, CENT, MONEY_CONTEXT'` exits 0
    - `python -c 'from decimal import Decimal; from lib.money import quantize_rate; print(quantize_rate(Decimal("0.0654995")))'` prints `0.065500`
    - `python -c 'from decimal import Decimal; from lib.money import quantize_rate; print(quantize_rate(Decimal("0.0654994")))'` prints `0.065499`
    - `mypy --strict lib/money.py` exits 0
    - `ruff check lib/money.py` exits 0
    - `ruff format --check lib/money.py` exits 0
  </acceptance_criteria>
  <done>
    lib/money.py exports a public, mypy-clean, ruff-clean quantize_rate that produces ROUND_HALF_UP behavior at the 6-decimal boundary; existing exports preserved.
  </done>
</task>

<task type="auto">
  <name>Task 2: Migrate lib/affordability.py — drop _quantize_rate def + rename 4 call sites + update imports</name>
  <files>lib/affordability.py</files>
  <read_first>
    - lib/affordability.py:174-187 (imports block) — Phase 5 ADDS quantize_rate to the existing `from lib.money import ...` line
    - lib/affordability.py:613-627 (_quantize_rate def + _RATE_QUANTUM Final constant) — Phase 5 REMOVES this entire block
    - lib/affordability.py around lines 930, 931, 945, 946 (4 call sites) — Phase 5 RENAMES `_quantize_rate(...)` to `quantize_rate(...)`
    - 05-RESEARCH.md §Q9 "Affordability.py update" subsection (lines 326-336)
  </read_first>
  <action>
    Make exactly three classes of edits to lib/affordability.py. The PUBLIC API of lib.affordability is UNCHANGED — only internals migrate.

    **Edit 1: Update the lib.money import.** In the existing line `from lib.money import MONEY_CONTEXT, quantize_cents` (around line 187), add `quantize_rate`:

    Before: `from lib.money import MONEY_CONTEXT, quantize_cents`
    After:  `from lib.money import MONEY_CONTEXT, quantize_cents, quantize_rate`

    **Edit 2: REMOVE the local `_quantize_rate` def + `_RATE_QUANTUM` constant.** Delete lines 613-627 entirely (the `_RATE_QUANTUM: Final[Decimal] = Decimal("0.000001")` constant, surrounding blank lines, and the entire `def _quantize_rate(...)` body and its docstring).

    Use the Edit tool to delete these 15 lines. After this edit, no `_quantize_rate` symbol exists in lib/affordability.py.

    **Edit 3: Rename 4 call sites.** Find every remaining `_quantize_rate(` in the file and replace with `quantize_rate(`. Per RESEARCH Q9 the call sites are at approximately lines 930, 931, 945, 946 — verify by grep before/after. There are exactly 4 call sites.

    **Important:** If you find more than 4 call sites OR fewer than 4, STOP and report — the codebase has drifted from RESEARCH and the plan needs revision. The expected count is exactly 4.

    **Important — also remove `from typing import Final` if it is now unused.** Use `mypy --strict` + `ruff check` to detect; ruff will flag F401 unused import. Keep `Final` if other constants in lib/affordability.py still use it (verify by grep for `: Final` after the edit).
  </action>
  <verify>
    <automated>bash -c 'cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; cp=$(grep -c "_quantize_rate" lib/affordability.py); cq=$(grep -c "_RATE_QUANTUM" lib/affordability.py); cu=$(grep -c "quantize_rate" lib/affordability.py); echo private=$cp RATE_QUANTUM=$cq public=$cu; test "$cp" = "0" &amp;&amp; test "$cq" = "0" &amp;&amp; test "$cu" -ge "5"'</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '_quantize_rate' lib/affordability.py` returns 0 (every reference renamed or removed)
    - `grep -c '_RATE_QUANTUM' lib/affordability.py` returns 0 (constant removed)
    - `grep -c 'quantize_rate' lib/affordability.py` returns at least 5 (1 import + 4 call sites)
    - `grep -c 'from lib.money import.*quantize_rate' lib/affordability.py` returns 1
    - `python -c 'from lib.affordability import evaluate'` exits 0 (public API still imports)
    - `mypy --strict lib/affordability.py` exits 0
    - `ruff check lib/affordability.py` exits 0
    - `ruff format --check lib/affordability.py` exits 0
  </acceptance_criteria>
  <done>
    lib/affordability.py no longer defines _quantize_rate or _RATE_QUANTUM; the file imports quantize_rate from lib.money and uses it at all 4 prior call sites; mypy + ruff clean.
  </done>
</task>

<task type="auto">
  <name>Task 3: Add golden-pin test for quantize_rate to tests/test_money.py</name>
  <files>tests/test_money.py</files>
  <read_first>
    - tests/test_money.py (full file) to understand existing test style (test class vs free function, fixture usage)
    - 05-RESEARCH.md §Q9 (line 341) recommendation
  </read_first>
  <action>
    Add a new test function `test_quantize_rate_round_half_up` to tests/test_money.py that pins the ROUND_HALF_UP behavior at the half-up boundary AND a few representative non-boundary cases. Match existing test style exactly (free function vs test class — whichever the file uses).

    Test cases to assert (use exact Decimal equality, never `assertAlmostEqual`):

    | Input (Decimal string) | Expected Output (Decimal string) | Reason |
    |---|---|---|
    | `"0.065"` | `"0.065000"` | typical Phase 4 affordability result; pads to 6 decimals |
    | `"0.0654995"` | `"0.065500"` | half-up boundary (exact halfway → rounds UP, not banker's even) |
    | `"0.0654994"` | `"0.065499"` | just below half → rounds DOWN |
    | `"0.0654996"` | `"0.065500"` | above half → rounds UP |
    | `"0.000000"` | `"0.000000"` | zero edge |
    | `"1.000000"` | `"1.000000"` | unit edge (max LTV scenario) |
    | `"0.123456789012345"` | `"0.123457"` | 28-digit-input clamps to 6 places (LTV math from affordability) |

    Test body (Python; if existing file uses class-based pattern, place inside the analogous class as a method with `self` parameter):

    ```
    def test_quantize_rate_round_half_up() -> None:
        """quantize_rate quantizes to 6 decimal places using ROUND_HALF_UP.

        Promoted from lib/affordability.py._quantize_rate (Phase 4 D-09) per
        Phase 5 D-14. The half-up boundary case (0.0654995 -> 0.065500) is
        the load-bearing pin: Python's default Decimal context is
        ROUND_HALF_EVEN (banker's rounding) which would produce 0.065498 —
        US consumer finance discipline (CLAUDE.md) requires HALF_UP.
        """
        from decimal import Decimal
        from lib.money import quantize_rate
        assert quantize_rate(Decimal("0.065")) == Decimal("0.065000")
        assert quantize_rate(Decimal("0.0654995")) == Decimal("0.065500")
        assert quantize_rate(Decimal("0.0654994")) == Decimal("0.065499")
        assert quantize_rate(Decimal("0.0654996")) == Decimal("0.065500")
        assert quantize_rate(Decimal("0.000000")) == Decimal("0.000000")
        assert quantize_rate(Decimal("1.000000")) == Decimal("1.000000")
        # 28-digit input (LTV math from affordability) clamps to 6 places
        assert quantize_rate(Decimal("0.123456789012345")) == Decimal("0.123457")
    ```

    If existing tests in test_money.py are at module level (free functions), add this as a free function. If they are inside a `class TestMoney:` (or similar), add this as a method of that class with a `self` parameter.

    Do not modify any existing tests in tests/test_money.py.
  </action>
  <verify>
    <automated>pytest tests/test_money.py -k test_quantize_rate_round_half_up -xvs</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'def test_quantize_rate_round_half_up' tests/test_money.py` returns 1
    - `grep -c 'Decimal("0.0654995")' tests/test_money.py` returns at least 1 (half-up boundary case present)
    - `grep -c 'Decimal("0.123456789012345")' tests/test_money.py` returns at least 1 (28-digit case present)
    - `pytest tests/test_money.py -k test_quantize_rate_round_half_up -x` exits 0 with 1 passed
    - `pytest tests/test_money.py -x` (full module) exits 0 with no failures
    - `mypy --strict tests/test_money.py` exits 0
    - `ruff check tests/test_money.py` exits 0
    - `ruff format --check tests/test_money.py` exits 0
  </acceptance_criteria>
  <done>
    tests/test_money.py contains test_quantize_rate_round_half_up; all 7 assertions pass with exact Decimal equality; mypy + ruff clean.
  </done>
</task>

<task type="auto">
  <name>Task 4: Verify zero regression to Phase 4 baseline + zero regression to Phase 3</name>
  <files>(verification only)</files>
  <read_first>
    - 05-RESEARCH.md §Q9 "Verification step" line 344
  </read_first>
  <action>
    Run the full pytest suite. The Phase 4 baseline is 379 passed + 4 skipped (per Phase 4 final SUMMARY in ROADMAP line 97). Phase 5 Wave 0 (Plan 05-00) added 32 xfails. After Wave 1:
    - Expected: ≥ 379 passed (was 379 in Phase 4), + 4 skipped (Phase 4 baseline), + 32 xfailed (Wave 0), + 1 NEW passed test (test_quantize_rate_round_half_up) → final pass count ≥ 380.
    - Acceptable variance: any pre-existing xfailed test that flips to pass (XPASS) is a Wave 0 strict=True failure — STOP and investigate.

    Run: `pytest -q`

    Then run mypy + ruff hygiene on every file Phase 5 Wave 1 touches:
    - `mypy --strict lib/money.py lib/affordability.py tests/test_money.py`
    - `ruff check lib/money.py lib/affordability.py tests/test_money.py`
    - `ruff format --check lib/money.py lib/affordability.py tests/test_money.py`

    All three MUST be clean (zero issues, zero diffs). If any fail, fix and re-run before declaring done.
  </action>
  <verify>
    <automated>pytest -q &amp;&amp; mypy --strict lib/money.py lib/affordability.py tests/test_money.py &amp;&amp; ruff check lib/money.py lib/affordability.py tests/test_money.py &amp;&amp; ruff format --check lib/money.py lib/affordability.py tests/test_money.py</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q` exits 0
    - `pytest -q` final summary line shows passed >= 380 (was 379 in Phase 4 + 1 new test from Task 3)
    - `pytest -q` final summary line shows xfailed exactly 32 (Wave 0 stubs all still xfail — no XPASS leak from this plan)
    - `pytest -q` final summary line shows failed = 0 and errors = 0
    - `mypy --strict lib/money.py lib/affordability.py tests/test_money.py` exits 0
    - `ruff check lib/money.py lib/affordability.py tests/test_money.py` exits 0
    - `ruff format --check lib/money.py lib/affordability.py tests/test_money.py` exits 0
    - `pytest tests/test_affordability.py -q` shows passed >= 379-modulo-skipped (verify Phase 4 closure preserved)
    - `pytest tests/test_amortize.py -q` shows passed = same as Phase 3 baseline (Phase 5 did not touch amortize.py — must be unchanged)
  </acceptance_criteria>
  <done>
    Full suite green; Phase 4 baseline preserved exactly; Phase 3 baseline unchanged; mypy + ruff clean across all touched files.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| lib.affordability internal API | The private `_quantize_rate` symbol disappears; any consumer (test, downstream phase) reaching into `lib.affordability._quantize_rate` would break |
| Phase 4 oracle anchors | The forward-mode round-trip closure (Phase 4 D-09 SC-2) depends on the exact ROUND_HALF_UP behavior of quantize_rate; semantic drift would silently change LTV/DTI computed values |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-08 | Tampering (Phase 4 regression) | _quantize_rate semantic | mitigate | Task 4 acceptance_criteria runs full pytest; the 379+4 baseline must hold byte-equivalent. The lifted code is character-for-character identical (same quantum, same context, same rounding mode), so behavior is provably unchanged |
| T-05-13 | Tampering (silent rounding-mode change) | quantize_rate body | mitigate | Task 3 golden-pin test asserts the half-up boundary value (0.0654995 → 0.065500); Python's default ROUND_HALF_EVEN would produce a different value, catching any accidental rounding-mode swap |
| T-05-14 | Information Disclosure (private import leak) | downstream import path | mitigate | Acceptance criteria asserts `_quantize_rate` symbol is GONE (count = 0); no test or future plan can leak through a private path |
| T-05-15 | Repudiation (mypy --strict regression) | type checking | mitigate | Task 4 acceptance_criteria runs mypy --strict on all 3 touched files; both lib/money.py and lib/affordability.py must pass |
</threat_model>

<verification>
- lib/money.py exports public quantize_rate; existing exports unchanged
- lib/affordability.py: zero matches for `_quantize_rate` and `_RATE_QUANTUM`; matches for `quantize_rate` ≥ 5
- Full pytest suite: ≥380 passed, exactly 32 xfailed, 0 failed, 0 errored
- mypy --strict + ruff clean across lib/money.py + lib/affordability.py + tests/test_money.py
- Phase 3 + Phase 4 individual suites still green (no regression)
</verification>

<success_criteria>
- D-14 promotion path complete: lib.money.quantize_rate is public; lib.affordability uses it via import; lib.arm (Wave 2+) can use the same import
- Phase 4 frozen surface preserved (public `evaluate` API unchanged; tests/test_affordability.py unchanged)
- Half-up rounding behavior pinned by golden-fixture test (catches accidental rounding-mode drift)
- Zero regression to Phase 3 + Phase 4 test counts
</success_criteria>

<output>
After completion, create `.planning/phases/05-arm-modeling/05-01-SUMMARY.md` documenting:
- lib/money.py line count delta (+18 expected)
- lib/affordability.py line count delta (-15 expected; -1 import line if `Final` removed)
- Phase 4 test count: 379 + 4 → 380 + 4 (+1 new test_quantize_rate_round_half_up)
- Wave 0 xfail count unchanged (still 32; no XPASS leak)
- mypy + ruff status across all 3 touched files
</output>
