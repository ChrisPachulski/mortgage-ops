---
phase: 11
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/test_subagents.py
  - tests/fixtures/subagent_transcripts/.gitkeep
  - tests/fixtures/subagent_transcripts/README.md
  - pyproject.toml
  - uv.lock
autonomous: true
requirements: []
tags:
  - phase-11
  - subagents
  - test-infrastructure
  - nyquist
  - tokenizer
must_haves:
  truths:
    - "tests/test_subagents.py file exists in repo and is collected by pytest"
    - "Every Phase 11 requirement (SUBA-01..06) has at least one stub function with @pytest.mark.xfail(strict=True) decorator"
    - "Stubbed file runs (pytest tests/test_subagents.py -v) without ImportError; xfail tests show as XFAIL not ERROR"
    - "tests/fixtures/subagent_transcripts/ directory is committed (via .gitkeep) and contains a README documenting the fixture-regeneration ritual"
    - "anthropic Python SDK is added to dev-deps in pyproject.toml at a pinned version; uv.lock updated"
    - "Phase 11 test scaffold is additive: introduces no behavior change to Phase 1..4 production code or existing tests; only adds new xfail-decorated stubs that downstream waves flip"
    - "Phase 4 baseline (379 passed + 4 skipped + 0 xfail) is preserved exactly modulo new Phase 11 xfails"
  artifacts:
    - path: "tests/test_subagents.py"
      provides: "6 xfail stubs covering SUBA-01..06; AGENTS_DIR/SKILLS_DIR/TRANSCRIPT_DIR module constants; _split_frontmatter helper"
      min_lines: 200
    - path: "tests/fixtures/subagent_transcripts/.gitkeep"
      provides: "Empty placeholder so the transcript-fixture directory is committed before fixtures land in Wave 5"
    - path: "tests/fixtures/subagent_transcripts/README.md"
      provides: "Documents the manual ritual for regenerating recorded subagent transcripts"
      min_lines: 30
    - path: "pyproject.toml"
      provides: "anthropic SDK pinned at exact version under [dependency-groups].dev"
      contains: "anthropic=="
  key_links:
    - from: "tests/test_subagents.py"
      to: "tests/fixtures/subagent_transcripts/"
      via: "TRANSCRIPT_DIR module constant"
      pattern: "TRANSCRIPT_DIR"
    - from: "Wave 5 plan (11-05 tests + transcript fixtures)"
      to: "tests/test_subagents.py xfail decorators"
      via: "incremental flip from xfail to pass as agent files + transcripts land"
      pattern: "@pytest.mark.xfail"
    - from: "tests/test_subagents.py SUBA-06 token-budget test"
      to: "anthropic.Anthropic().messages.count_tokens"
      via: "pytest.importorskip('anthropic') + pytest.mark.skipif on missing ANTHROPIC_API_KEY"
      pattern: "count_tokens"
---

<objective>
Establish the Phase 11 test scaffolding that subsequent waves flip xfail to pass against. Ship `tests/test_subagents.py` with 6 xfail-decorated stub tests (one per SUBA-01..06), the empty `tests/fixtures/subagent_transcripts/` directory + a README documenting the fixture-regeneration ritual, and add the `anthropic` Python SDK to dev-deps at a pinned version (per RESEARCH.md tokenizer choice: anthropic.count_tokens, NOT tiktoken).

Purpose: Nyquist validation gate. Every requirement-closing wave (Plans 01..06) flips a specific xfail to a real assertion. Without Wave 0, downstream plans have no test landing pads — they would either ship agent files with no tests or invent test names ad-hoc. Also pre-commits the SDK choice so SUBA-06's count_tokens call has a stable import path before the agent-file plans run.

Output: A test file that COLLECTS but xfails everything; an empty fixture directory + its regeneration README; one pyproject.toml dependency edit + uv.lock refresh. Zero agent code, zero transcript content.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/11-subagents/11-PATTERNS.md
@.planning/phases/11-subagents/11-RESEARCH.md
@CLAUDE.md
@tests/conftest.py
@tests/test_amortize.py
@tests/test_reference/test_schema.py
@pyproject.toml

<interfaces>
Existing tests/conftest.py — Phase 11 does NOT extend conftest.py (transcripts loaded inline via TRANSCRIPT_DIR module constant). Mirror SCRIPT_PATH from tests/test_amortize.py:51 + parametrized filesystem-introspection from tests/test_reference/test_schema.py:19-36.

Phase 4 baseline pre-Wave-0: 379 passed + 4 skipped + 0 xfail (per ROADMAP).

Anthropic SDK API surface (per 11-RESEARCH.md Code Example 5):

```python
import anthropic
client = anthropic.Anthropic()
response = client.messages.count_tokens(
    model="claude-haiku-4-5",
    messages=[{"role": "assistant", "content": "<text>"}],
)
assert response.input_tokens < 1000
```

`count_tokens` is FREE (no content billing) but DOES require ANTHROPIC_API_KEY at runtime — that is why SUBA-06 ships with @pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY")). All other SUBA-01..05 stubs are filesystem-only and run unconditionally in CI.

DATA_CONTRACT: subagents READ household.yml/profile.yml only; never write.

Cross-phase HARD DEPENDENCY: Phase 11 implementation is BLOCKED until Phase 10 (SKLL-01..13) lands `.claude/skills/mortgage-ops/SKILL.md` + `modes/stress.md` + relocated `scripts/`. Wave 0 does NOT depend on Phase 10 (it ships only test scaffolding + dev-dep + fixture dir); Waves 1..6 explicitly state the Phase-10 gate in their Dependencies sections.
</interfaces>

<test_inventory>
The 6 xfail stubs created in tests/test_subagents.py — names verbatim per RESEARCH.md "Phase Requirements to Test Map":

SUBA-01 (1 stub) — flipped in Wave 1 (amortization-agent.md ships):
- test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields

SUBA-02 (1 stub) — flipped in Wave 2 (refi-npv-agent.md ships):
- test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet

SUBA-03 (1 stub) — flipped in Wave 3 (stress-test-agent.md ships):
- test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku

SUBA-04 (1 stub) — flipped in Wave 5 (parametrized across all 3 agents):
- test_SUBA_04_each_agent_skills_field_is_mortgage_ops

SUBA-05 (1 stub) — flipped in Wave 4 (modes/stress.md routing rule lands):
- test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent

SUBA-06 (1 stub) — flipped in Wave 5 (transcript fixture + count_tokens call land):
- test_SUBA_06_stress_summary_under_1k_tokens

TOTAL: 6 xfail stubs.

Note: Wave 5 may add ADDITIONAL non-SUBA tests (skill-resolution smoke, refi-3-offer table, amortize CSV-or-markdown table) when transcripts are available; those are NEW tests added at flip time, not stubs flipped from xfail.
</test_inventory>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Pin anthropic SDK as a dev dep in pyproject.toml + uv lockfile</name>
  <files>pyproject.toml, uv.lock</files>
  <read_first>
    - pyproject.toml lines 1-50 (existing [dependency-groups].dev block)
    - 11-RESEARCH.md "Standard Stack" section (anthropic >=0.40 line) + "Installation" subsection
    - 11-RESEARCH.md "Pitfall 4" — count_tokens response shape has changed between SDK versions; pin TIGHT (==X.Y.Z), not loose (>=)
  </read_first>
  <action>
    Resolve the current latest `anthropic` SDK version, then pin it exactly:

    1. Run `pip index versions anthropic 2>/dev/null | head -2` to discover the current latest version. (If `pip index` is unavailable, fall back to reading https://pypi.org/pypi/anthropic/json or `uv pip install --dry-run anthropic 2>&1`.)
    2. Note the resolved version (call it X.Y.Z).
    3. Run `uv add --group dev "anthropic==X.Y.Z"` from the repo root. This both edits pyproject.toml and refreshes uv.lock.
    4. Verify: `uv sync` is idempotent; `uv run python -c "import anthropic; print(anthropic.__version__)"` prints X.Y.Z.

    Per RESEARCH Pitfall 4 — DO NOT use `>=0.40` or any loose specifier. The count_tokens response shape (.input_tokens vs .usage.input_tokens) has shifted between SDK majors and a tight pin keeps Wave 5's SUBA-06 test reproducible. Bumps happen DELIBERATELY in a follow-up plan, never transitively.

    Per CLAUDE.md global rule — commit message MUST NOT include any Co-Authored-By or AI attribution.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv sync &amp;&amp; uv run python -c "import anthropic; print('anthropic', anthropic.__version__)" &amp;&amp; grep -c 'anthropic==' pyproject.toml</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'anthropic==' pyproject.toml` returns 1 (exact-pin specifier present)
    - `grep -cE 'anthropic[~^>]=' pyproject.toml` returns 0 (no loose specifier)
    - `uv run python -c "import anthropic; print(anthropic.__version__)"` exits 0 and prints the pinned version
    - `uv sync` exits 0 (idempotent)
    - `test -f uv.lock` exits 0 (lockfile present)
    - `grep -c '"anthropic"' uv.lock` returns at least 1 (anthropic appears in lockfile)
  </acceptance_criteria>
  <done>
    anthropic SDK is pinned at an exact version in dev-deps; uv.lock is refreshed and reproducible; import succeeds.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create tests/fixtures/subagent_transcripts/ directory + regeneration README</name>
  <files>tests/fixtures/subagent_transcripts/.gitkeep, tests/fixtures/subagent_transcripts/README.md</files>
  <read_first>
    - tests/fixtures/ existing layout (mirror the .gitkeep convention used in tests/fixtures/arm/ from Phase 5)
    - 11-RESEARCH.md "Pattern 5: SUBA-06 token-budget test (transcript fixture)" — describes the regeneration ritual
    - CLAUDE.md (READ-ONLY user layer + no commit attribution)
  </read_first>
  <action>
    1. Create `tests/fixtures/subagent_transcripts/.gitkeep` as a zero-byte file (Write tool, content="").

    2. Create `tests/fixtures/subagent_transcripts/README.md` documenting the regeneration ritual. Required sections (verbatim headers):

       - `# Subagent Transcript Fixtures` (top-level)
       - `## Why recorded, not live?` — explain that live LLM dispatch in CI is non-deterministic, burns credits, and requires interactive Claude Code; recorded transcripts are deterministic + free + regenerable. Cite 11-RESEARCH "Anti-Patterns to Avoid" and "Pitfall 3".
       - `## Files` — enumerate the three transcripts that Wave 5 will ship: `stress_50_scenario_summary.md` (SUBA-06 oracle, target < 1000 tokens), `refi_3_offer_ranked.md` (SUBA-04 refi assertion), `amortize_single_loan.md` (SUBA-04 amortize assertion).
       - `## How to regenerate a transcript` — 5-step ritual: (1) confirm Phase 10 has shipped the skill + scripts, restart Claude Code per Pitfall 3; (2) dispatch the agent in an interactive session with the canonical prompt; (3) copy ONLY the agent's RETURNED message (not its internal working text) to the corresponding `.md`; (4) run `uv run pytest tests/test_subagents.py -v` to confirm SUBA-04/SUBA-06 still pass; (5) commit the regenerated transcript alongside any agent-file edits.
       - `## What NOT to put here` — no PII / household.yml data (synthetic inputs only per DATA_CONTRACT.md); no raw 50-scenario JSON dumps (per Pitfall 5; if a transcript exceeds 1000 tokens, fix the agent prompt — do not raise the budget).

       Minimum 30 lines. Plain markdown, no triple-backtick fences for the section bodies (avoids escaping issues at this nesting). Do NOT add Co-Authored-By trailers anywhere.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; test -f tests/fixtures/subagent_transcripts/.gitkeep &amp;&amp; test -f tests/fixtures/subagent_transcripts/README.md &amp;&amp; test "$(wc -c &lt; tests/fixtures/subagent_transcripts/.gitkeep)" -eq 0 &amp;&amp; test "$(wc -l &lt; tests/fixtures/subagent_transcripts/README.md)" -ge 30</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/fixtures/subagent_transcripts/.gitkeep` exits 0
    - `test -f tests/fixtures/subagent_transcripts/README.md` exits 0
    - `wc -c tests/fixtures/subagent_transcripts/.gitkeep` returns 0 (empty file)
    - `wc -l tests/fixtures/subagent_transcripts/README.md` returns at least 30
    - `grep -c '## Why recorded' tests/fixtures/subagent_transcripts/README.md` returns 1
    - `grep -c '## How to regenerate' tests/fixtures/subagent_transcripts/README.md` returns 1
    - `grep -c '## What NOT to put here' tests/fixtures/subagent_transcripts/README.md` returns 1
    - `grep -c 'stress_50_scenario_summary' tests/fixtures/subagent_transcripts/README.md` returns at least 1
    - `grep -c 'ANTHROPIC_API_KEY' tests/fixtures/subagent_transcripts/README.md` returns at least 1
    - `grep -ci 'co-authored-by' tests/fixtures/subagent_transcripts/README.md` returns 0
  </acceptance_criteria>
  <done>
    Both files exist; README documents regeneration; directory is committable.
  </done>
</task>

<task type="auto">
  <name>Task 3: Create tests/test_subagents.py with 6 xfail stubs covering SUBA-01..06</name>
  <files>tests/test_subagents.py</files>
  <read_first>
    - tests/test_amortize.py lines 1-60 (module header + SCRIPT_PATH constant + import pattern)
    - tests/test_reference/test_schema.py lines 1-36 (parametrized filesystem-introspection meta-test pattern)
    - 11-RESEARCH.md "Code Examples" Example 4 + Example 5 (the SUBA-01 frontmatter parse + SUBA-06 token-budget test bodies — Wave 5 will use these as templates when flipping)
    - 11-PATTERNS.md "tests/test_subagents.py" section (specifically the _parse_frontmatter helper shape)
  </read_first>
  <action>
    Create tests/test_subagents.py as a brand-new file. The file holds exactly 6 xfail-decorated stub tests + module header + module-level path constants + a _split_frontmatter helper that Wave 5 will reuse when flipping. NO test asserts anything except `pytest.fail("Wave 0 stub")` (the xfail marker absorbs the failure into XFAIL state).

    File structure (write verbatim):

    ```python
    """Phase 11 Subagents — full SUBA-01..06 test surface.

    Per 11-RESEARCH.md tokenizer choice: SUBA-06 uses anthropic.count_tokens
    against a recorded transcript fixture (NOT tiktoken; tiktoken is OpenAI-
    specific and explicitly rejected). All SUBA-01..05 stubs are filesystem-
    only (yaml.safe_load + regex on modes/stress.md + Path.exists smoke); they
    run unconditionally in CI without ANTHROPIC_API_KEY.

    Wave 0 (Plan 11-00) creates ALL 6 tests as xfail stubs. Subsequent waves
    flip the relevant xfail decorators to real assertions:

    - Wave 1 (Plan 11-01): SUBA-01 amortization-agent.md frontmatter parse
    - Wave 2 (Plan 11-02): SUBA-02 refi-npv-agent.md frontmatter (model=sonnet)
    - Wave 3 (Plan 11-03): SUBA-03 stress-test-agent.md frontmatter (model=haiku)
    - Wave 4 (Plan 11-04): SUBA-05 modes/stress.md routing rule (>5 scenarios)
    - Wave 5 (Plan 11-05): SUBA-04 (parametrized over 3 agents) + SUBA-06
      (transcript fixture + count_tokens call); MAY add new non-stub tests
      for skill-resolution smoke + refi/amortize transcript shape.

    Each xfail decorator carries `strict=True` so a passing test in xfail state
    raises XPASS at collection time — the wave that flips it MUST also remove
    the decorator. This prevents accidental "fixed but still marked xfail" drift.

    HARD DEPENDENCY: SUBA-04 and SUBA-05 cannot pass until Phase 10 ships
    .claude/skills/mortgage-ops/SKILL.md + modes/stress.md. Wave 0 only ships
    the stubs; flip happens in Waves 4 + 5 AFTER Phase 10 lands.
    """

    from __future__ import annotations

    import os
    from pathlib import Path
    from typing import TYPE_CHECKING, Any

    import pytest

    if TYPE_CHECKING:
        pass

    AGENTS_DIR: Path = Path(__file__).resolve().parent.parent / ".claude" / "agents"
    """Phase 11 ships .claude/agents/{amortization,refi-npv,stress-test}-agent.md.
    Project-scope per Anthropic spec — version-controlled, NOT user-scope (~/.claude/agents/)."""

    SKILLS_DIR: Path = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops"
    """Phase 10 ships .claude/skills/mortgage-ops/. Phase 11 SUBA-04 + SUBA-05
    smoke tests assert the skill + bundled scripts exist at this path."""

    TRANSCRIPT_DIR: Path = Path(__file__).resolve().parent / "fixtures" / "subagent_transcripts"
    """Phase 11 Wave 5 ships recorded transcripts here. SUBA-06 reads
    stress_50_scenario_summary.md and pipes it through anthropic.count_tokens."""

    EXPECTED_AGENTS = ("amortization-agent", "refi-npv-agent", "stress-test-agent")
    """Locked agent name set per ROADMAP SC-1 + REQUIREMENTS SUBA-01..03."""

    VALID_MODELS = frozenset({"haiku", "sonnet", "opus", "inherit"})
    """Short-alias model whitelist per 11-PATTERNS.md CRITICAL #1a recommendation
    (alias over fully-qualified ID so model-class upgrades don't require touching
    three agent files)."""

    REQUIRED_FRONTMATTER_KEYS = frozenset({"name", "description", "model", "skills"})
    """SUBA-01 contract per ROADMAP SC-1: every agent must declare these keys."""


    def _split_frontmatter(md_path: Path) -> dict[str, Any]:
        """Parse the YAML frontmatter from a markdown agent file.

        Spec: file starts with '---\\n', frontmatter ends at next '---\\n', body follows.
        Lifted verbatim from 11-PATTERNS.md "_parse_frontmatter" pattern (mirrors
        tests/test_reference/test_schema.py YAML-loading idiom).

        Wave 0 ships this helper but does NOT call it (all stubs xfail before
        invocation); Wave 1+ uses it when flipping. Imported lazily inside the
        helper to keep --collect-only fast even if pyyaml grows expensive.
        """
        import yaml  # noqa: PLC0415 — intentional lazy import for collect-only speed

        text = md_path.read_text()
        if not text.startswith("---\\n"):
            raise ValueError(f"{md_path}: missing opening '---' frontmatter delimiter")
        parts = text.split("---\\n", 2)
        if len(parts) < 3:
            raise ValueError(f"{md_path}: missing closing '---' frontmatter delimiter")
        return yaml.safe_load(parts[1])  # type: ignore[no-any-return]


    # =========================================================================
    # SUBA-01 (1 stub) — flipped in Wave 1 (Plan 11-01 ships amortization-agent.md)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-01 ships .claude/agents/amortization-agent.md")
    def test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields() -> None:
        """SUBA-01 + ROADMAP SC-1: amortization-agent.md frontmatter has model:, skills: [mortgage-ops], description, name."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # SUBA-02 (1 stub) — flipped in Wave 2 (Plan 11-02 ships refi-npv-agent.md)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-02 ships .claude/agents/refi-npv-agent.md")
    def test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet() -> None:
        """SUBA-02 + ROADMAP SC-4: refi-npv-agent.md frontmatter parses AND model=sonnet (Sonnet for multi-step NPV ranking)."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # SUBA-03 (1 stub) — flipped in Wave 3 (Plan 11-03 ships stress-test-agent.md)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-03 ships .claude/agents/stress-test-agent.md")
    def test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku() -> None:
        """SUBA-03: stress-test-agent.md frontmatter parses AND model=haiku.

        REQUIREMENTS.md SUBA-03 originally said Haiku; orchestrator brief said
        'TBD'; PATTERNS.md CRITICAL #1a surfaced the discrepancy. RESEARCH
        recommended Haiku because the reasoning load is 'compress table to
        representative shape', not multi-step composition. PINNED HAIKU here.
        """
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # SUBA-04 (1 stub, parametrized over 3 agents in Wave 5) — flipped in Wave 5
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-05 parametrizes over EXPECTED_AGENTS")
    def test_SUBA_04_each_agent_skills_field_is_mortgage_ops() -> None:
        """SUBA-04 + ROADMAP SC-5: every agent declares skills: [mortgage-ops] (Phase 10 dependency)."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # SUBA-05 (1 stub) — flipped in Wave 4 (Plan 11-04 lands modes/stress.md routing rule)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-04 lands the >5 routing rule in modes/stress.md (Phase 10 file)")
    def test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent() -> None:
        """SUBA-05 + ROADMAP SC-2: modes/stress.md documents 'sweeps with > 5 scenarios route to stress-test-agent'."""
        pytest.fail("Wave 0 stub")


    # =========================================================================
    # SUBA-06 (1 stub) — flipped in Wave 5 (Plan 11-05 ships transcript + count_tokens call)
    # =========================================================================

    @pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-05 ships stress_50_scenario_summary.md + count_tokens assertion")
    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="SUBA-06 token-budget test requires ANTHROPIC_API_KEY (count_tokens is FREE but requires the key per platform.claude.com/docs/en/build-with-claude/token-counting)",
    )
    def test_SUBA_06_stress_summary_under_1k_tokens() -> None:
        """SUBA-06 + ROADMAP SC-3: 50-scenario rate-shock summary fits under 1000 tokens.

        Uses anthropic.Anthropic().messages.count_tokens(model='claude-haiku-4-5', ...)
        against tests/fixtures/subagent_transcripts/stress_50_scenario_summary.md.
        tiktoken explicitly REJECTED per 11-RESEARCH.md (OpenAI-specific, drifts ±20%).
        """
        pytest.fail("Wave 0 stub")
    ```

    Key details:
    - All 6 stubs use `@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-XX ...")`. The strict flag means a stub that ACCIDENTALLY passes raises XPASS and fails CI — forcing the wave that fixes the test to also remove the decorator.
    - SUBA-06 carries an ADDITIONAL `@pytest.mark.skipif` on missing ANTHROPIC_API_KEY (xfail evaluates AFTER skipif, so when the key is absent the test reports SKIPPED, not XFAIL — that is correct behavior).
    - Module-level path constants (AGENTS_DIR, SKILLS_DIR, TRANSCRIPT_DIR) + EXPECTED_AGENTS + VALID_MODELS + REQUIRED_FRONTMATTER_KEYS are shipped now so flip-plans don't re-derive them.
    - `_split_frontmatter` helper is shipped now (lazy-imports yaml inside) so flip-plans just call it.
    - NO real assertions in Wave 0 — every body is `pytest.fail("Wave 0 stub")`.

    The module docstring is the canonical wave-flip map; subsequent plans must honor those wave assignments.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run pytest tests/test_subagents.py -v --tb=no 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/test_subagents.py` exits 0
    - `wc -l tests/test_subagents.py` returns at least 200
    - `grep -c '@pytest.mark.xfail(strict=True' tests/test_subagents.py` returns 6 (one per stub)
    - `grep -c 'def test_' tests/test_subagents.py` returns 6
    - `grep -c 'def test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields' tests/test_subagents.py` returns 1
    - `grep -c 'def test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet' tests/test_subagents.py` returns 1
    - `grep -c 'def test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku' tests/test_subagents.py` returns 1
    - `grep -c 'def test_SUBA_04_each_agent_skills_field_is_mortgage_ops' tests/test_subagents.py` returns 1
    - `grep -c 'def test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent' tests/test_subagents.py` returns 1
    - `grep -c 'def test_SUBA_06_stress_summary_under_1k_tokens' tests/test_subagents.py` returns 1
    - `grep -c 'AGENTS_DIR: Path = Path(__file__).resolve().parent.parent / ".claude" / "agents"' tests/test_subagents.py` returns 1
    - `grep -c 'SKILLS_DIR: Path = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops"' tests/test_subagents.py` returns 1
    - `grep -c 'TRANSCRIPT_DIR: Path = Path(__file__).resolve().parent / "fixtures" / "subagent_transcripts"' tests/test_subagents.py` returns 1
    - `grep -c 'def _split_frontmatter' tests/test_subagents.py` returns 1
    - `grep -v '^[[:space:]]*#' tests/test_subagents.py | grep -c 'tiktoken'` returns 0 (no tiktoken import, even commented in code body — only in docstring narrative is acceptable)
    - `uv run pytest tests/test_subagents.py --collect-only -q 2>&1 | grep -c '::test_'` returns at least 6
    - `uv run pytest tests/test_subagents.py -v --tb=no 2>&1 | grep -cE '(XFAIL|SKIP)'` returns 6 (every stub either xfails or, for SUBA-06 without API key, skips)
    - `uv run pytest tests/test_subagents.py -v --tb=no 2>&1 | grep -cE '(FAILED|ERROR)'` returns 0 (no errors / collect failures)
  </acceptance_criteria>
  <done>
    tests/test_subagents.py is collected by pytest, runs to completion, and produces exactly 6 XFAIL-or-SKIP outcomes (zero passes, zero failures, zero errors).
  </done>
</task>

<task type="auto">
  <name>Task 4: Verify zero regression to Phase 4/5 baseline + run mypy + ruff</name>
  <files>(verification only — no file writes)</files>
  <read_first>
    - 11-RESEARCH.md "Validation Architecture / Sampling Rate" — full suite green is the phase gate
    - Phase 4 baseline: 379 passed + 4 skipped + 0 xfail (per ROADMAP)
  </read_first>
  <action>
    Run the full pytest suite and confirm:
    1. Phase 4 baseline preserved: at least 379 passed + 4 skipped (Phase 5 may add additional passes if its waves are landing in parallel — that is acceptable; the floor must hold)
    2. Phase 11 adds exactly 6 new XFAIL-or-SKIP outcomes (depending on whether ANTHROPIC_API_KEY is set in the local env)
    3. Zero failures, zero errors

    Run: `uv run pytest -v --tb=short 2>&1 | tail -80`

    If any pre-existing test fails or any unexpected error appears, STOP and investigate. Do NOT proceed until full suite is green-modulo-xfail.

    After verification passes, run mypy + ruff hygiene on the new file and the (unchanged but rechecked) conftest:
    - `uv run mypy --strict tests/test_subagents.py`
    - `uv run ruff check tests/test_subagents.py tests/fixtures/subagent_transcripts/README.md`
    - `uv run ruff format --check tests/test_subagents.py`

    All MUST be clean (zero issues, zero diffs). pyproject.toml does not need ruff/mypy checks (it's a TOML config file).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops &amp;&amp; uv run pytest -q 2>&amp;1 | tail -5 &amp;&amp; uv run mypy --strict tests/test_subagents.py &amp;&amp; uv run ruff check tests/test_subagents.py &amp;&amp; uv run ruff format --check tests/test_subagents.py</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest -q 2>&1 | tail -3 | grep -oE '[0-9]+ passed' | head -1` shows at least 379 passed
    - `uv run pytest -q 2>&1 | tail -3 | grep -cE '[0-9]+ (failed|error)'` returns 0 OR matches lines that say "0 failed" / "0 errors"
    - `uv run pytest tests/test_subagents.py -q 2>&1 | tail -3 | grep -cE '(xfailed|skipped)'` shows the 6 new outcomes accounted for (6 xfailed if API key absent the SUBA-06 may report skipped)
    - `uv run mypy --strict tests/test_subagents.py` exits 0 with "Success: no issues found"
    - `uv run ruff check tests/test_subagents.py` exits 0 with "All checks passed"
    - `uv run ruff format --check tests/test_subagents.py` exits 0
  </acceptance_criteria>
  <done>
    Full suite passes with zero regressions; new tests show 6 XFAIL/SKIP outcomes; mypy + ruff clean across all touched Python files.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Wave 0 → Waves 1..6 | Test stubs define the contract that agent implementations must satisfy; mismatch silently leaves a SUBA-XX requirement unverified |
| pytest collection → CI signal | XFAIL (or SKIP for SUBA-06 sans API key) must be the outcome state; PASS or FAIL or ERROR all leak signal noise |
| pyproject.toml dev-dep edit → uv.lock | Loose `>=` specifier risks count_tokens response-shape drift between SDK versions; tight `==` pin mitigates |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-01 | Tampering (test contract drift) | tests/test_subagents.py stub names | mitigate | Stub names are LISTED VERBATIM in the test_inventory frontmatter section; acceptance_criteria grep each one to confirm presence |
| T-11-02 | Information Disclosure (false-pass via skipped xfail) | xfail decorators | mitigate | Every xfail uses `strict=True` so an accidental pass triggers XPASS failure. Waves 1..5 plans MUST remove the decorator when flipping the test |
| T-11-03 | Tampering (count_tokens response-shape drift breaks CI silently) | anthropic SDK pin | mitigate | Tight `==X.Y.Z` pin in pyproject.toml + uv.lock. Bumps are deliberate, never transitive. Pitfall 4 in RESEARCH.md documents the exact failure mode. |
| T-11-04 | Information Disclosure (transcript fixtures leak PII) | tests/fixtures/subagent_transcripts/README.md | mitigate | README explicitly forbids household.yml or PII content; synthetic-input requirement documented; reviewer checks transcripts at PR time |
| T-11-05 | Repudiation (silent regression to Phase 4/5 baseline) | new test file + dep edit | mitigate | Task 4 acceptance_criteria asserts ≥379 passed; mypy + ruff clean |
| T-11-06 | Denial of Service (test-suite slowdown from new stubs) | 6 new xfail stubs | accept | All stubs are zero-cost `pytest.fail("Wave 0 stub")`; total runtime impact < 0.1s |
</threat_model>

<verification>
- All 6 expected stub names present in tests/test_subagents.py (one grep per name in acceptance_criteria)
- Module-level constants (AGENTS_DIR, SKILLS_DIR, TRANSCRIPT_DIR, EXPECTED_AGENTS, VALID_MODELS, REQUIRED_FRONTMATTER_KEYS) defined
- _split_frontmatter helper present and importable
- anthropic SDK pinned exactly in pyproject.toml; uv.lock refreshed
- tests/fixtures/subagent_transcripts/.gitkeep + README.md committed
- Full pytest suite: ≥379 passed + 6 new xfail/skip + 0 failed + 0 errored
- mypy --strict + ruff clean across tests/test_subagents.py
</verification>

<success_criteria>
- tests/test_subagents.py exists, collected by pytest, all 6 stubs report XFAIL or (SUBA-06 only) SKIP
- pyproject.toml [dependency-groups].dev contains `anthropic==X.Y.Z` (exact pin); uv.lock includes anthropic
- tests/fixtures/subagent_transcripts/ committed via .gitkeep + README.md (≥30 lines, documents regeneration ritual)
- Phase 4 baseline preserved (≥379 passed + ≥4 skipped)
- mypy --strict + ruff clean across tests/test_subagents.py
- Waves 1..5 have a clear contract: each downstream plan flips a known SUBA-XX xfail and removes the strict decorator
- No Co-Authored-By or AI attribution in any committed file or commit message (per CLAUDE.md global rule)
</success_criteria>

<deviation_rules>
- If `pip index versions anthropic` is unavailable AND PyPI JSON read fails: fall back to `uv add --group dev anthropic` (lets uv resolve), then capture the resolved version from uv.lock and re-edit pyproject.toml to pin that exact version. Do NOT leave a `>=` specifier.
- If Wave 0 runs while Phase 5 ARM stubs are still xfail: that is fine; the pass-floor assertion (≥379) tolerates additional xfail counts. Do NOT touch Phase 5 tests.
- If `anthropic` SDK install fails on the developer machine (network / proxy): document the failure in the SUMMARY but still ship the test file + README + .gitkeep. SUBA-06 will report SKIP locally; CI must inject the key.
- If `_split_frontmatter` helper triggers ruff TCH or PLC0415 warnings on the lazy yaml import: keep the lazy import (it is intentional per the docstring) and add `# noqa: PLC0415` inline if needed. Do NOT promote yaml to a top-level import — that would slow `pytest --collect-only` for the entire test suite, not just this module.
</deviation_rules>

<dependencies>
**Wave 0 dependencies — none. This wave is fully self-contained:**

- No Phase 10 dependency: Wave 0 ships only test scaffolding + dev-dep + fixture dir. The xfail stubs reference `.claude/skills/mortgage-ops/` paths only via module-level Path constants that are NOT touched (no Path.exists() / read_text() in Wave 0 code paths).
- No upstream Phase 11 plan dependency (Wave 0 IS the upstream).
- Phase 4 must be complete (it is — 7/7 plans, 379 passed). Phase 5 may be in flight; Wave 0 does not collide with it (different test file, different fixtures dir).

**Downstream dependencies (informational):**

- Waves 1..3 depend on Wave 0 (need the xfail stubs to flip)
- Wave 4 depends on Wave 0 + Phase 10 SKLL-05 (modes/stress.md must exist)
- Wave 5 depends on Waves 0..4 + Phase 10 SKLL-01..13 (all skill artifacts must exist; bundled scripts must be reachable for SUBA-04/05 smoke)
- Wave 6 depends on Waves 0..5 (final docs ship after agents work)

**Cross-phase HARD GATE:** Phase 11 IMPLEMENTATION (Waves 4 + 5 specifically) is BLOCKED until Phase 10 lands `.claude/skills/mortgage-ops/SKILL.md`, `.claude/skills/mortgage-ops/modes/stress.md`, and the relocated `.claude/skills/mortgage-ops/scripts/{amortize,refi_npv,stress_test}.py`. The executor MUST verify Phase 10 status before starting Waves 4 + 5. Waves 0..3 + 6 do NOT require Phase 10.
</dependencies>

<output>
After completion, create `.planning/phases/11-subagents/11-00-SUMMARY.md` documenting:
- Number of xfail stubs created (must be 6)
- anthropic SDK version pinned (e.g., "anthropic==0.42.0")
- Phase 4/5 baseline pass count after Wave 0 (must be ≥379)
- mypy + ruff status (must be clean)
- Mapping table: each xfail stub → wave-and-plan responsible for flipping it
- Confirmation that no Co-Authored-By trailers appear in the commit
</output>
