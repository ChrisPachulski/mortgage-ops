---
phase: 10
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/conftest.py
  - tests/test_skill.py
  - tests/_skill_helpers.py
  - tests/fixtures/skill/.gitkeep
  - pyproject.toml
autonomous: true
requirements:
  - SKLL-01
  - SKLL-02
  - SKLL-03
  - SKLL-04
  - SKLL-05
  - SKLL-06
  - SKLL-07
  - SKLL-08
  - SKLL-09
  - SKLL-10
  - SKLL-11
  - SKLL-12
  - SKLL-13
tags:
  - phase-10
  - claude-skill
  - test-infrastructure
  - nyquist
must_haves:
  truths:
    - "tests/test_skill.py exists in repo and is collected by pytest"
    - "Every Phase 10 requirement (SKLL-01..13) has at least one xfail-decorated stub function — including SKLL-13 per D-13-01..05 (Phase 10 closes SKLL-13; NOT deferred)"
    - "Stubbed file runs (`pytest tests/test_skill.py -v`) without ImportError; xfail tests show as XFAIL not ERROR"
    - "tests/_skill_helpers.py exposes count_tokens(text) helper using tiktoken cl100k_base (D-02), reusable by Phase 11/12"
    - "tests/conftest.py exposes skill_root pytest fixture returning Path(.claude/skills/mortgage-ops)"
    - "pyproject.toml [dependency-groups].dev includes tiktoken>=0.7,<1.0 (D-02 enforcement dep)"
    - "Phase 10 test scaffold is additive: introduces no behavior change to Phase 1..5 production code or existing tests; only adds new xfail-decorated stubs that downstream waves flip"
    - "tests/test_skill.py passes `ruff check` (no F401 unused-import) at Wave 0 commit time — imports needed only by Wave 5 assertions are deferred into the test bodies that use them"
  artifacts:
    - path: "tests/test_skill.py"
      provides: "≥ 15 xfail stubs covering SKLL-01..SKLL-13 (including 2 new SKLL-13 stubs per D-13-05) + cross-cutting envelope/help-doctrine tests"
      min_lines: 200
      contains: "def test_skill_md_under_token_budget"
    - path: "tests/_skill_helpers.py"
      provides: "Shared tiktoken cl100k_base token-counting helper for Phase 10/11/12 (per RESEARCH §i + D-02)"
      contains: "def count_tokens"
    - path: "tests/conftest.py"
      provides: "skill_root fixture returning Path(.claude/skills/mortgage-ops) for cross-test reuse"
      contains: "def skill_root"
    - path: "tests/fixtures/skill/.gitkeep"
      provides: "Empty placeholder so future skill fixtures (e.g. invocation captures) commit cleanly"
    - path: "pyproject.toml"
      provides: "tiktoken>=0.7,<1.0 added to [dependency-groups].dev for SKLL-01 enforcement"
      contains: "tiktoken"
  key_links:
    - from: "tests/test_skill.py"
      to: "tests/_skill_helpers.py"
      via: "from tests._skill_helpers import count_tokens"
      pattern: "from tests._skill_helpers import"
    - from: "tests/test_skill.py"
      to: "tests/conftest.py"
      via: "skill_root fixture parametric injection"
      pattern: "def test_.*\\(.*skill_root"
    - from: "Wave 1..5 plans"
      to: "tests/test_skill.py xfail decorators"
      via: "incremental flip from xfail → pass as relocation/scaffold/modes/refs/CI tests land"
      pattern: "@pytest.mark.xfail"
---

<objective>
Establish the Phase 10 test scaffolding that subsequent waves flip xfail→pass against. Ship the `skill_root` pytest fixture, the `tests/_skill_helpers.py` tiktoken token-counting helper (per LOCKED DECISION D-02), ≥ 15 xfail-decorated stub tests covering every SKLL-01..13 requirement (including 2 new SKLL-13 stubs per D-13-05 — Phase 10 closes SKLL-13, NOT deferred to Phase 9), the empty `tests/fixtures/skill/` directory, and the `tiktoken>=0.7,<1.0` dev-dep addition to `pyproject.toml`.

Purpose: Nyquist validation gate. Every requirement-closing wave (Plans 10-01 through 10-05) flips a specific xfail to a real assertion. Without Wave 0, downstream plans have no test landing pads — they would either ship code with no test or invent test names ad-hoc.

Output: A test file that COLLECTS but xfails everything; a `_skill_helpers.py` shared harness for Phase 10/11/12 reuse; a conftest.py extension; one empty fixture directory; one pyproject.toml dev-dep addition. Zero skill content, zero scripts moved.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/10-claude-skill/10-CONTEXT.md
@.planning/phases/10-claude-skill/10-PATTERNS.md
@.planning/phases/10-claude-skill/10-RESEARCH.md
@.planning/phases/10-claude-skill/10-UI-SPEC.md
@CLAUDE.md
@DATA_CONTRACT.md
@tests/conftest.py
@tests/test_arm.py
@pyproject.toml

<interfaces>
LOCKED DECISIONS (from 10-RESEARCH §"Locked Decisions D-01..D-12" + 10-CONTEXT.md D-13-01..05):
- D-01 = MOVE relocation (deferred to Wave 1)
- D-02 = tiktoken cl100k_base @ ≤ 4500 tokens with documented 10% Anthropic-tokenizer margin (THIS WAVE creates the helper; Wave 5 wires the assertion)
- D-03..D-12 = SKILL.md frontmatter / LICENSE / cross-phase contract / progressive disclosure rules (downstream waves)
- **D-13-01..D-13-05 (10-CONTEXT.md): Phase 10 CLOSES SKLL-13.** modes/_shared.md adds a "Save Report" step that writes `reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md` then calls `node orchestration/db-write.mjs --insert-report --json {meta}`. Wave 0 ships TWO new SKLL-13 stubs (D-13-05); Wave 5 flips them.

Phase 5 Plan 05-00 xfail-stub pattern (lift verbatim shape) — every stub uses
`@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-XX implements ...")`
plus body `pytest.fail("Wave 0 stub")`. The strict flag means an accidentally-passing stub raises XPASS → CI fail → forces the wave that fixes it to also remove the decorator.

Existing tests/conftest.py exposes 4 fixtures (golden_fixture, amortize_fixture, affordability_fixture, arm_fixture) — all callable-loaders. The skill_root fixture appended in this plan returns a Path CONSTANT (not a callable), because callers want a path not a per-test loader.

**Ruff F401 hygiene:** Wave 0 ships ONLY xfail stubs whose bodies are `pytest.fail("Wave 0 stub")`. Top-of-file imports (`re`, `subprocess`, `sys`, `yaml`, `count_tokens`) are not used by any stub body, so `ruff check` flags them as F401 unused-import. To keep `ruff check` green at Wave 0 commit, ALL such imports MUST be deferred — placed inside the eventual flipped-test bodies in Wave 5, NOT at module level. Module-level imports at Wave 0 are limited to `pytest` and `from __future__ import annotations` (used by xfail decorator + type hints) and `from pathlib import Path` (used in test signatures `skill_root: Path`).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add tiktoken>=0.7,<1.0 to pyproject.toml [dependency-groups].dev (D-02 dep gate)</name>
  <files>pyproject.toml</files>
  <read_first>
    pyproject.toml lines 13-19 (existing [dependency-groups].dev block);
    10-RESEARCH §(i) D-02 — pin rationale (tiktoken 0.7+ latest at research time)
  </read_first>
  <action>
Edit `pyproject.toml`. In the existing `[dependency-groups]` block (lines 13-19), append `"tiktoken>=0.7,<1.0",` to the `dev` list, alphabetized.

Current list (lines 14-19):
```
dev = [
    "pytest>=9.0",
    "mypy>=1.20",
    "ruff>=0.15",
    "pre-commit>=4.6",
]
```

After edit (alphabetized):
```
dev = [
    "mypy>=1.20",
    "pre-commit>=4.6",
    "pytest>=9.0",
    "ruff>=0.15",
    "tiktoken>=0.7,<1.0",
]
```

DO NOT touch any other section of pyproject.toml. The ruff `src` and mypy `files` lines are EXPRESSLY DEFERRED to Plan 10-01 (Wave 1) per LOCKED DECISION D-01; editing them here would create a sync gap with the actual file moves.

After the edit, run `uv sync --quiet` so `uv.lock` updates and tiktoken becomes importable.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; grep -q 'tiktoken' pyproject.toml &amp;&amp; uv sync --quiet &amp;&amp; python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"</automated>
  </verify>
  <acceptance_criteria>
- `grep -c 'tiktoken' pyproject.toml` returns ≥ 1
- `grep -c 'src = ' pyproject.toml` returns 1 (UNCHANGED at this wave)
- `grep -c 'files = ' pyproject.toml` returns ≥ 1 (UNCHANGED at this wave)
- `python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"` exits 0
- `uv.lock` mtime newer than before (or `uv sync` ran successfully)
  </acceptance_criteria>
  <done>
    tiktoken is importable; pyproject.toml has the new dev-dep; no other pyproject sections touched.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create tests/_skill_helpers.py with count_tokens() shared harness</name>
  <files>tests/_skill_helpers.py</files>
  <read_first>
    10-PATTERNS.md `tests/_skill_helpers.py` section;
    10-RESEARCH §(i) D-02 — full Anthropic-vs-cl100k margin rationale;
    scripts/_cli_helpers.py — Phase 5 factor-extract pattern for shared test helpers
  </read_first>
  <action>
Create `tests/_skill_helpers.py` (NEW FILE). The leading underscore marks it as a non-test test-package module; pytest won't collect it for tests but `from tests._skill_helpers import ...` works because `tests/__init__.py` exists.

File content (~45 lines):

```python
"""Shared skill/eval token-counting harness.

Phase 10 ships this; Phase 11 SUBA-06 imports for the < 1000-token subagent
summary assertion; Phase 12 EVAL-04 imports for eval-harness budget checks.

Per Phase 10 RESEARCH §(i) + LOCKED DECISION D-02: tiktoken cl100k_base for
CI-friendly, deterministic, network-free token counting. Anthropic does not
publish their tokenizer; multiple sources (propelcode.ai, gopenai.com) report
cl100k undercounts the actual Anthropic tokenizer by ~10-15% for English
prose with markdown. We document a 10% safety margin so callers know to
enforce thresholds proportionally lower than Anthropic-spec recommendations
(e.g., enforce ≤ 4500 cl100k for a nominal 5000 Anthropic budget; ≤ 900
cl100k for a nominal 1000 Anthropic budget).
"""

from __future__ import annotations

import tiktoken

_ENCODER = tiktoken.get_encoding("cl100k_base")
"""Module-level encoder — cheap to construct, but cached so repeat callers
in the same pytest session don't re-resolve the BPE tables."""


def count_tokens(text: str) -> int:
    """Return the cl100k_base token count for *text*.

    cl100k is OpenAI's BPE tokenizer (gpt-3.5/4 era). It is an APPROXIMATION
    of Anthropic's tokenizer — see module docstring for the ~10-15% margin
    rationale. Callers MUST apply a safety margin when enforcing token
    budgets against Anthropic-spec thresholds.
    """
    return len(_ENCODER.encode(text))


def assert_under_budget(
    text: str, hard_budget: int, *, safety_margin_pct: int = 10
) -> None:
    """Assert ``count_tokens(text) <= hard_budget * (1 - safety_margin_pct/100)``.

    Raises AssertionError with a message including the measured count and
    the effective cap. Callers should pass the Anthropic-spec budget as
    *hard_budget* (e.g., 5000 for SKILL.md SKLL-01).
    """
    effective = int(hard_budget * (100 - safety_margin_pct) / 100)
    n = count_tokens(text)
    assert n <= effective, (
        f"token budget exceeded: {n} cl100k tokens > {effective} "
        f"(hard cap {hard_budget} Anthropic; {safety_margin_pct}% safety "
        f"margin per RESEARCH §i + D-02)"
    )
```

Hygiene constraints:
- mypy --strict clean (all public functions typed)
- ruff clean (imports sorted; double-quoted strings; line-length ≤ 100)
- No imports from `tests.conftest` (cycle would form once conftest imports back)

DO NOT write a test file for this helper — Task 3 covers it indirectly via test_skill_md_under_token_budget. Phase 11 SUBA-06 will write its own test that imports count_tokens.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; python -c "from tests._skill_helpers import count_tokens, assert_under_budget; print(count_tokens('hello world'))" &amp;&amp; mypy --strict tests/_skill_helpers.py &amp;&amp; ruff check tests/_skill_helpers.py &amp;&amp; ruff format --check tests/_skill_helpers.py</automated>
  </verify>
  <acceptance_criteria>
- File `tests/_skill_helpers.py` exists with at least 40 lines
- `grep -c 'def count_tokens' tests/_skill_helpers.py` returns 1
- `grep -c 'def assert_under_budget' tests/_skill_helpers.py` returns 1
- `grep -c 'cl100k_base' tests/_skill_helpers.py` returns ≥ 1
- `python -c "from tests._skill_helpers import count_tokens; assert count_tokens('') == 0"` exits 0
- `mypy --strict tests/_skill_helpers.py` exits 0
- `ruff check tests/_skill_helpers.py` exits 0
- `ruff format --check tests/_skill_helpers.py` exits 0
  </acceptance_criteria>
  <done>
    Helper is importable, both public functions work, mypy + ruff clean.
  </done>
</task>

<task type="auto">
  <name>Task 3: Extend tests/conftest.py with skill_root fixture + create tests/fixtures/skill/.gitkeep</name>
  <files>tests/conftest.py, tests/fixtures/skill/.gitkeep</files>
  <read_first>
    tests/conftest.py (full file) — existing fixture shape;
    10-RESEARCH §"Wave 0 Gaps" — `skill_root` returns a Path constant (not a callable)
  </read_first>
  <action>
PART A — Append to `tests/conftest.py` after the last existing fixture. The skill_root fixture differs from the *_fixture pattern: returns a Path CONSTANT (not a callable).

Append exactly this block at end of file:

```python


@pytest.fixture
def skill_root() -> Path:
    """Return the absolute path to .claude/skills/mortgage-ops/ for cross-test reuse.

    Phase 10 ships this fixture so every Phase 10/11/12 test that introspects
    the skill folder (SKILL.md, modes/, references/, scripts/, LICENSE.txt)
    has a single source of truth for the path. The folder may not exist at
    Wave 0 time (Plans 10-01 through 10-05 create it); tests that depend on
    existence MUST assert that explicitly.

    Per LOCKED DECISION D-01: the skill folder lives at
    .claude/skills/mortgage-ops/ (project-relative).
    """
    return Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops"
```

DO NOT modify any existing fixture (golden_fixture, amortize_fixture, affordability_fixture, arm_fixture).

PART B — Create `tests/fixtures/skill/.gitkeep` as an empty (zero-byte) file. Phase 10 doesn't ship invocation-capture fixtures yet; Phase 11/12 will. Committing the directory now establishes the seam.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; python -c "import pytest; from tests import conftest; print('skill_root' in dir(conftest))" &amp;&amp; test -f tests/fixtures/skill/.gitkeep &amp;&amp; test ! -s tests/fixtures/skill/.gitkeep</automated>
  </verify>
  <acceptance_criteria>
- `grep -c 'def skill_root' tests/conftest.py` returns 1
- `grep -c 'def golden_fixture' tests/conftest.py` returns 1 (UNCHANGED)
- `grep -c 'def amortize_fixture' tests/conftest.py` returns 1 (UNCHANGED)
- `grep -c 'def affordability_fixture' tests/conftest.py` returns 1 (UNCHANGED)
- `grep -c 'def arm_fixture' tests/conftest.py` returns 1 (UNCHANGED)
- `test -f tests/fixtures/skill/.gitkeep` exits 0
- `wc -c tests/fixtures/skill/.gitkeep` returns 0
- `pytest tests/test_amortize.py tests/test_affordability.py tests/test_arm.py --collect-only -q` exits 0
  </acceptance_criteria>
  <done>
    skill_root fixture is importable; existing fixtures unchanged; existing test collection still succeeds; .gitkeep committed.
  </done>
</task>

<task type="auto">
  <name>Task 4: Create tests/test_skill.py with ≥ 15 xfail stubs covering SKLL-01..13 (including 2 new SKLL-13 stubs per D-13-05)</name>
  <files>tests/test_skill.py</files>
  <read_first>
    tests/test_arm.py (full file, ~545 lines) — verbatim shape of xfail-stub module from Phase 5 Plan 05-00;
    10-PATTERNS.md `tests/test_skill_structure.py` section — full sketch of SKLL-01..13 test names and bodies;
    10-RESEARCH §"Phase Requirements → Test Map" — 1:1 SKLL-XX → test name mapping;
    10-CONTEXT.md D-13-01..05 — Phase 10 CLOSES SKLL-13 with auto-write reports + DuckDB ingest; D-13-05 mandates ≥ 2 new SKLL-13 stubs (filename format + DB persistence)
  </read_first>
  <action>
Create `tests/test_skill.py` as a brand-new file. The file holds ≥ 15 xfail-decorated stub tests + a module header. NO test asserts anything except `pytest.fail("Wave 0 stub")` (the xfail marker absorbs the failure into XFAIL state).

**RUFF F401 HYGIENE (CRITICAL):** Wave 0 stub bodies do NOT use `re`, `subprocess`, `sys`, `yaml`, or `count_tokens`. Per `ruff check` defaults (F401 unused-import is enabled), placing them at module level fails CI. Two acceptable resolutions:
  (a) **Preferred:** OMIT these imports from Wave 0; Wave 5 plan re-adds them at module level when bodies actually use them. Wave 0 module-level imports limited to: `from __future__ import annotations`, `from pathlib import Path` (used in test signatures), `import pytest` (used by xfail decorators).
  (b) **Fallback:** Add `# noqa: F401` to each currently-unused import. Less clean but acceptable.

Use APPROACH (a). Wave 5 plans (Plan 10-05 + Plan 10-06) explicitly re-add `import re`, `import subprocess`, `import sys`, `import yaml`, `from tests._skill_helpers import count_tokens` when the assertions that use them are wired in.

File structure (lift the docstring + import + xfail-decorator pattern verbatim from `tests/test_arm.py:1-65`):

```python
"""Phase 10 Claude Skill Frontend — full test surface (SKLL-01..13).

Wave 0 (Plan 10-00) creates ALL ≥ 15 tests as xfail stubs. Subsequent waves
flip the relevant xfail decorators to real assertions:

- Wave 1 (Plan 10-01 scripts relocation):    SKLL-10                     (1 test)
- Wave 2 (Plan 10-02 SKILL.md scaffold):      SKLL-01..04, SKLL-11..12   (7 tests)
- Wave 3 (Plan 10-03 modes/*):                SKLL-05..07                (3 tests)
- Wave 4 (Plan 10-04 references/*):           SKLL-08..09                (2 tests)
- Wave 5 (Plan 10-05 CI tests + ports):       SKLL-13 (per D-13-01..05; 2 stubs)

Per LOCKED DECISION D-02: the token-budget assertion uses
tests._skill_helpers.count_tokens (tiktoken cl100k_base) with a 10% safety
margin against the 5000-token Anthropic spec recommendation; effective
threshold = 4500 cl100k tokens.

Per LOCKED DECISION D-12: SKLL-02 enforcement parses the first 200 lines of
SKILL.md and asserts the mode dispatch table marker (`## Mode Routing`) is
present.

Per CONTEXT.md D-13-01..D-13-05: Phase 10 CLOSES SKLL-13 (NOT deferred to
Phase 9). Two new stubs ship in Wave 0 and flip in Wave 5: filename-format
test (reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md per D-13-02) and DuckDB-row
persistence test (per D-13-04 — `node orchestration/db-write.mjs --insert-report`).

Each xfail decorator carries `strict=True` so a passing test in xfail state
raises XPASS at collection time — the wave that flips it MUST also remove
the decorator. This prevents accidental "fixed but still marked xfail" drift
(Phase 5 D-XX hygiene contract inherited).

Note: imports for `re`, `subprocess`, `sys`, `yaml`, `count_tokens` are NOT
included at module level in Wave 0 — they would trigger ruff F401
(unused-import) since stub bodies use only `pytest.fail`. Wave 5 (Plan 10-05)
adds these imports at module level when the flipped assertions consume them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# SKLL-01 (2 stubs) — flipped in Wave 5 (CI tests). Uses count_tokens helper
# from Wave 0; threshold per D-02.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-02 ships SKILL.md; Plan 10-05 wires assertion")
def test_skill_md_under_token_budget(skill_root: Path) -> None:
    """SKLL-01 + ROADMAP SC-1: SKILL.md ≤ 4500 cl100k tokens (10% under 5000 Anthropic spec)."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-02 ships SKILL.md; Plan 10-05 wires assertion")
def test_skill_md_under_line_budget(skill_root: Path) -> None:
    """SKLL-01 + ROADMAP SC-1: SKILL.md ≤ 500 lines."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-02 (1 stub) — flipped in Wave 5; per D-12 grep-assert mode-routing
# in first 200 lines.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-02 ships routing skeleton; Plan 10-05 wires assertion")
def test_skill_routing_in_first_200_lines(skill_root: Path) -> None:
    """SKLL-02 + D-12: '## Mode Routing' + 7 mode names appear in first 200 lines of SKILL.md."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-03 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-02 ships frontmatter; Plan 10-05 wires assertion")
def test_skill_md_frontmatter_required_fields(skill_root: Path) -> None:
    """SKLL-03 + ROADMAP SC-2: frontmatter has name, description, license, compatibility."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-04 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-02 ships LICENSE.txt; Plan 10-05 wires assertion")
def test_license_txt_exists_in_skill_folder(skill_root: Path) -> None:
    """SKLL-04 + ROADMAP SC-2: LICENSE.txt bundled inside skill folder (D-04 = MIT default)."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-05 (1 stub) — flipped in Wave 5; parametrized over 7 modes
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-03 ships modes/*.md; Plan 10-05 wires parametrize")
def test_modes_exist(skill_root: Path) -> None:
    """SKLL-05 + ROADMAP SC-4: 7 mode files (evaluate, compare, refinance, affordability, stress, amortize, arm) exist under modes/."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-06 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-03 ships modes/_shared.md; Plan 10-05 wires assertion")
def test_shared_mode_has_required_sections(skill_root: Path) -> None:
    """SKLL-06 + ROADMAP SC-4: modes/_shared.md defines scoring + report structure (career-ops pattern + UI-SPEC §i)."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-07 (1 stub) — flipped in Wave 5; per D-07 .example.md pattern
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-03 ships .example.md template + gitignore; Plan 10-05 wires assertion")
def test_profile_md_user_layer_gitignored(skill_root: Path) -> None:
    """SKLL-07 + D-07: modes/_profile.md gitignored AND modes/_profile.example.md committed."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-07 / D-PROF-01 (1 stub) — _profile.example.md schema enforcement.
# Asserts the example schema parses as YAML AND has EXACTLY the four
# top-level keys (verbosity, citation_density, save_report, disambiguation),
# no extras. Flipped in Wave 5.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-03 ships D-PROF-01 schema; Plan 10-05 wires assertion")
def test_profile_example_md_has_exact_four_keys(skill_root: Path) -> None:
    """D-PROF-01 + D-PROF-02: _profile.example.md YAML body has EXACTLY these
    four top-level keys: verbosity, citation_density, save_report, disambiguation.
    No extras (calc inputs stay in config/household.yml + config/profile.yml)."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-08 (1 stub) — flipped in Wave 5; parametrized over 9 references
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-04 ships references/*.md; Plan 10-05 wires parametrize")
def test_references_exist(skill_root: Path) -> None:
    """SKLL-08 + ROADMAP SC-5: 9 reference files (amortization-formulas, apr-reg-z, arm-mechanics, refi-npv, affordability-rules, gse-limits, mip-pmi, tax-deductibility, spreadsheet-conventions) exist under references/."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-09 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-02 ships progressive-disclosure rule; Plan 10-05 wires assertion")
def test_skill_md_documents_progressive_disclosure(skill_root: Path) -> None:
    """SKLL-09 + ROADMAP SC-5 + D-09: SKILL.md contains a topic→reference table for on-demand reference loading."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-10 (1 stub) — flipped in Wave 1 (relocation); per D-01 + D-06 + D-08.
# Asserts ALL SEVEN calc scripts live INSIDE the skill folder. Phase 6/7/8
# scripts (refi_npv.py, apr_reg_z.py, stress_test.py, points_breakeven.py)
# are confirmed shipped per STATE.md (Phase 6/7/8 COMPLETE) so all 7 scripts
# can be relocated together in Plan 10-01 Task 2.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-01 relocates 7 calc scripts (amortize, affordability, arm_simulate, refi_npv, apr_reg_z, stress_test, points_breakeven) + _cli_helpers; flipped same wave")
def test_seven_scripts_in_skill_folder_only(skill_root: Path) -> None:
    """SKLL-10 + ROADMAP SC-3 + D-01 + D-06 + D-08: ALL SEVEN calc scripts —
    amortize.py, affordability.py, arm_simulate.py, refi_npv.py, apr_reg_z.py,
    stress_test.py, points_breakeven.py — live ONLY in
    .claude/skills/mortgage-ops/scripts/, NOT at project root scripts/.
    _cli_helpers.py also relocates with them.

    _generate_arm_fixtures.py + scripts/hooks/ STAY at project root (D-06,
    dev tooling, not user-facing CLIs).

    STATE.md confirms Phases 6/7/8 COMPLETE — all 7 scripts exist at project
    root and CAN be relocated together. SC-3 / SKLL-10 close FULLY in Phase 10."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-11 (1 stub) — flipped in Wave 5
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-02 ships math-discipline doctrine in SKILL.md; Plan 10-05 wires assertion")
def test_skill_md_shell_out_doctrine(skill_root: Path) -> None:
    """SKLL-11 + ROADMAP SC-5 + UI-SPEC §g: SKILL.md contains the literal substring 'ALWAYS shell out' (or near-equivalent — assert by regex match per UI-SPEC narration template)."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-12 (1 stub) — flipped in Wave 5; per webapp-testing exemplar doctrine
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-02 ships --help-first doctrine; Plan 10-05 wires assertion")
def test_each_script_has_help_and_doctrine_documented(skill_root: Path) -> None:
    """SKLL-12 + ROADMAP SC-5: each relocated script's `--help` exits 0 in < 200ms, AND SKILL.md contains 'run --help first; do not read source' (or near-equivalent literal text)."""
    pytest.fail("Wave 0 stub")


# ---------------------------------------------------------------------------
# SKLL-13 (2 stubs per D-13-05) — Phase 10 CLOSES SKLL-13. NOT deferred.
# Per CONTEXT.md D-13-01..05: modes/_shared.md ships a "Save Report" step
# that writes reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md and persists via
# `node orchestration/db-write.mjs --insert-report`. Wave 5 flips both.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-03 ships Save Report step in _shared.md (D-13-01..05); Plan 10-05 wires assertion")
def test_report_filename_format(skill_root: Path) -> None:
    """SKLL-13 + D-13-02: report filenames follow reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md
    convention (3-digit zero-padded sequence, mode slug from {evaluate, compare,
    refinance, affordability, stress, amortize, arm}, ISO date). Wave 5 wires
    by inducing a save (or by parsing modes/_shared.md for the convention)
    and regex-matching the filename."""
    pytest.fail("Wave 0 stub")


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-03 ships db-write.mjs --insert-report integration (D-13-04); Plan 10-05 wires assertion (Plan 10-06 adds end-to-end smoke)")
def test_report_persisted_to_duckdb(skill_root: Path) -> None:
    """SKLL-13 + D-13-04: after writing reports/{NNN}-{mode}-{date}.md, the
    skill calls `node orchestration/db-write.mjs --insert-report --json
    {scenario_id, kind, markdown_blob, filename}`. Test asserts that
    SELECT COUNT(*) FROM reports WHERE filename = ? returns 1 after a
    simulated save. Wave 5 ships the unit-level assertion; Plan 10-06
    adds an end-to-end smoke that actually invokes the Save Report path."""
    pytest.fail("Wave 0 stub")
```

Notes:
- ≥ 15 stubs total: SKLL-01 has 2 (token + line); SKLL-02..09 each have 1 (= 8); SKLL-07/D-PROF-01 has 1; SKLL-10..12 each have 1 (= 3); SKLL-13 has 2 (= 16 total). The "≥ 15" floor accommodates either the 16-stub layout above or a planner choice to fold the D-PROF-01 stub into SKLL-07.
- All stubs use `@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 10-XX ...")`.
- Module-level imports limited to `from __future__ import annotations`, `from pathlib import Path`, `import pytest` — Wave 5 ADDS the rest when needed.
- Each stub body is just `pytest.fail("Wave 0 stub")`.
- SKLL-13 (D-13-01..05) closure stubs MUST be present — codex review HIGH severity called out their absence as the largest contract mismatch.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest tests/test_skill.py -v --tb=no 2&gt;&amp;1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
- File `tests/test_skill.py` exists with at least 200 lines
- `grep -c '@pytest.mark.xfail(strict=True' tests/test_skill.py` returns ≥ 15
- `grep -c 'def test_' tests/test_skill.py` returns ≥ 15
- `grep -c 'def test_skill_md_under_token_budget' tests/test_skill.py` returns 1
- `grep -c 'def test_skill_routing_in_first_200_lines' tests/test_skill.py` returns 1
- `grep -c 'def test_skill_md_frontmatter_required_fields' tests/test_skill.py` returns 1
- `grep -c 'def test_license_txt_exists_in_skill_folder' tests/test_skill.py` returns 1
- `grep -c 'def test_modes_exist' tests/test_skill.py` returns 1
- `grep -c 'def test_shared_mode_has_required_sections' tests/test_skill.py` returns 1
- `grep -c 'def test_profile_md_user_layer_gitignored' tests/test_skill.py` returns 1
- `grep -c 'def test_profile_example_md_has_exact_four_keys' tests/test_skill.py` returns 1
- `grep -c 'def test_references_exist' tests/test_skill.py` returns 1
- `grep -c 'def test_skill_md_documents_progressive_disclosure' tests/test_skill.py` returns 1
- `grep -c 'def test_seven_scripts_in_skill_folder_only' tests/test_skill.py` returns 1
- `grep -c 'def test_skill_md_shell_out_doctrine' tests/test_skill.py` returns 1
- `grep -c 'def test_each_script_has_help_and_doctrine_documented' tests/test_skill.py` returns 1
- `grep -c 'def test_report_filename_format' tests/test_skill.py` returns 1 (SKLL-13 D-13-02)
- `grep -c 'def test_report_persisted_to_duckdb' tests/test_skill.py` returns 1 (SKLL-13 D-13-04)
- `grep -c '^import re' tests/test_skill.py` returns 0 (deferred; ruff F401 hygiene)
- `grep -c '^import subprocess' tests/test_skill.py` returns 0 (deferred)
- `grep -c '^import sys' tests/test_skill.py` returns 0 (deferred)
- `grep -c '^import yaml' tests/test_skill.py` returns 0 (deferred)
- `grep -c 'from tests._skill_helpers' tests/test_skill.py` returns 0 (deferred)
- `pytest tests/test_skill.py --collect-only -q` exits 0 (≥ 15 tests collected, no errors)
- `pytest tests/test_skill.py -v --tb=no 2>&1 | grep -c XFAIL` returns ≥ 15 (every stub xfails cleanly)
- `pytest tests/test_skill.py -v --tb=no 2>&1 | grep -E '(FAILED|ERROR)' | wc -l` returns 0
- `ruff check tests/test_skill.py` exits 0 (NO F401 unused-import errors)
  </acceptance_criteria>
  <done>
    tests/test_skill.py is collected by pytest, runs to completion, produces ≥ 15 XFAIL outcomes, and `ruff check` is clean (no F401 violations).
  </done>
</task>

<task type="auto">
  <name>Task 5: Verify zero regression to Phase 5 baseline + commit Wave 0</name>
  <files>(verification only — no file writes)</files>
  <read_first>
    Phase 5 SUMMARY (.planning/phases/05-arm-modeling/05-06-SUMMARY.md) — last-known baseline pass count
  </read_first>
  <action>
Run the full pytest suite and confirm:
1. Phase 5 baseline preserved: ≥ 432 passed (per ROADMAP Phase 5 row "432 passed + 4 skipped + 1 strict xfail"). The 432 floor must hold; any prior xfail flipping to pass is also acceptable.
2. New Phase 10 stubs show ≥ 15 xfails.
3. Zero failures, zero errors.

Run: `pytest -q 2>&1 | tail -10`

If any pre-existing test fails or any unexpected error appears, STOP and investigate. Do NOT proceed until full suite is green-modulo-xfail.

After verification passes, run mypy + ruff hygiene:
- `mypy --strict tests/conftest.py tests/test_skill.py tests/_skill_helpers.py`
- `ruff check tests/conftest.py tests/test_skill.py tests/_skill_helpers.py`
- `ruff format --check tests/conftest.py tests/test_skill.py tests/_skill_helpers.py`

All three MUST be clean. If `ruff check tests/test_skill.py` reports F401 unused-import errors, REVISIT Task 4 — the offending imports MUST be deferred to Wave 5 per the F401 hygiene rule.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; pytest -q 2&gt;&amp;1 | tail -10 &amp;&amp; mypy --strict tests/conftest.py tests/test_skill.py tests/_skill_helpers.py &amp;&amp; ruff check tests/conftest.py tests/test_skill.py tests/_skill_helpers.py &amp;&amp; ruff format --check tests/conftest.py tests/test_skill.py tests/_skill_helpers.py</automated>
  </verify>
  <acceptance_criteria>
- `pytest -q` shows ≥ 432 passed
- `pytest -q` shows ≥ 15 additional xfailed (Phase 10 stubs)
- `pytest -q` shows 0 failed, 0 errored
- mypy --strict clean across all 3 touched test files
- ruff check + format check clean across all 3 touched test files (NO F401 errors)
  </acceptance_criteria>
  <done>
    Full suite passes with zero regressions; Phase 10 stubs show ≥ 15 XFAIL; mypy + ruff clean.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Wave 0 → Wave 1..5 | Test stubs define the contract that subsequent plans must satisfy; mismatch silently leaves a SKLL requirement unverified |
| pytest collection → CI signal | XFAIL must be the outcome state; PASS or FAIL or ERROR all leak signal noise |
| tiktoken dep add → uv.lock | Stale uv.lock would prevent test_skill_md_under_token_budget from importing the helper |
| ruff F401 → Wave 0 commit | Imports placed prematurely (used only by Wave 5 bodies) fail `ruff check` and block the Wave 0 commit |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-01 | Tampering (test contract drift) | tests/test_skill.py stub names | mitigate | Stub names are LISTED VERBATIM in Task 4 acceptance_criteria as ≥ 15 explicit grep checks (including the 2 new SKLL-13 stubs per D-13-05) |
| T-10-02 | Information Disclosure (false-pass via skipped xfail) | xfail decorators | mitigate | Every xfail uses `strict=True` → accidental pass triggers XPASS failure (Phase 5 D-XX hygiene inherited) |
| T-10-03 | Denial of Service (test-suite slowdown) | new ≥ 15 stubs | accept | All stubs are zero-cost `pytest.fail("Wave 0 stub")`; total runtime impact < 0.5s |
| T-10-04 | Repudiation (silent regression to Phase 5 baseline) | conftest.py + pyproject.toml edits | mitigate | Task 5 acceptance asserts ≥ 432 passed + mypy + ruff clean |
| T-10-05 | Tampering (tiktoken pin drift) | pyproject.toml dev group | mitigate | Pin is `>=0.7,<1.0` per D-02; major-version bumps will fail CI explicitly |
| T-10-36 | Tampering (ruff F401 blocks Wave 0 commit) | premature top-level imports | mitigate | Task 4 mandates module-level imports limited to `pytest`/`pathlib.Path`/`__future__`; Wave 5 plans re-add the rest. Acceptance criteria explicitly grep -c each banned import returns 0. |
</threat_model>

<verification>
- All ≥ 15 expected stub names present in tests/test_skill.py (one grep per name)
- Two new SKLL-13 stubs present per D-13-05 (test_report_filename_format + test_report_persisted_to_duckdb)
- One D-PROF-01 stub present (test_profile_example_md_has_exact_four_keys)
- Module-level imports limited to `__future__`, `pathlib`, `pytest` (no F401 violations)
- Full pytest suite: ≥ 432 passed + ≥ 15 xfailed + 0 failed + 0 errored
- mypy --strict + ruff clean across conftest.py + test_skill.py + _skill_helpers.py
- skill_root fixture importable; existing fixtures unchanged
- tiktoken importable; uv.lock updated
- tests/fixtures/skill/.gitkeep committed (zero bytes)
</verification>

<success_criteria>
- tests/test_skill.py exists, collected by pytest, all ≥ 15 stubs report XFAIL
- tests/_skill_helpers.py exposes count_tokens + assert_under_budget
- tests/conftest.py extended with skill_root (existing fixtures untouched)
- tests/fixtures/skill/.gitkeep committed
- pyproject.toml has tiktoken>=0.7,<1.0 in [dependency-groups].dev
- Phase 5 baseline preserved (≥ 432 passed)
- mypy --strict + ruff format clean across all touched files (NO F401)
- Wave 1..5 have a clear contract: each downstream plan flips a known xfail name and removes the decorator
- SKLL-13 has TWO landing-pad stubs per D-13-05 (Phase 10 closes SKLL-13; not deferred)
</success_criteria>

<output>
After completion, create `.planning/phases/10-claude-skill/10-00-SUMMARY.md` documenting:
- Number of xfail stubs created (must be ≥ 15)
- Phase 5 baseline pass count after Wave 0 (must be ≥ 432)
- mypy + ruff status (must be clean — NO F401)
- Mapping table: each xfail stub → wave-and-plan responsible for flipping it
- SKLL-13 closure stubs (test_report_filename_format + test_report_persisted_to_duckdb) confirmed present per D-13-05 (Phase 10 closes SKLL-13)
- Confirmation that module-level imports are deferred (no F401 violations)
</output>
</content>
</invoke>