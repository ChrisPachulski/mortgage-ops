"""Phase 11 Subagents — full SUBA-01..06 test surface.

Per 11-RESEARCH.md tokenizer choice: SUBA-06 uses anthropic.count_tokens
against a recorded transcript fixture (NOT any OpenAI tokenizer; OpenAI's
BPE is explicitly rejected because it is not Tiktoken-compatible with the
Claude tokenizer). All SUBA-01..05 stubs are filesystem-only
(yaml.safe_load + regex on modes/stress.md + Path.exists smoke); they
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

Module structure (so Wave 1+ can drop in real assertions without
rederiving constants):

- AGENTS_DIR / SKILLS_DIR / TRANSCRIPT_DIR — anchored Path constants
- EXPECTED_AGENTS — locked agent name tuple per ROADMAP SC-1
- VALID_MODELS — short-alias whitelist per PATTERNS CRITICAL #1a
- REQUIRED_FRONTMATTER_KEYS — SUBA-01 contract per ROADMAP SC-1
- _split_frontmatter() — YAML frontmatter helper (lazy yaml import)

Subsequent waves should NOT redefine any of the above. They should
import them from this module if a sibling test file is added, or extend
them in place when a new agent / model alias / required key is locked.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Module-level path constants
# ---------------------------------------------------------------------------

AGENTS_DIR: Path = Path(__file__).resolve().parent.parent / ".claude" / "agents"
"""Phase 11 ships .claude/agents/{amortization,refi-npv,stress-test}-agent.md.
Project-scope per Anthropic spec — version-controlled, NOT user-scope (~/.claude/agents/)."""

SKILLS_DIR: Path = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops"
"""Phase 10 ships .claude/skills/mortgage-ops/. Phase 11 SUBA-04 + SUBA-05
smoke tests assert the skill + bundled scripts exist at this path."""

TRANSCRIPT_DIR: Path = Path(__file__).resolve().parent / "fixtures" / "subagent_transcripts"
"""Phase 11 Wave 5 ships recorded transcripts here. SUBA-06 reads
stress_50_scenario_summary.md and pipes it through anthropic.count_tokens."""

# ---------------------------------------------------------------------------
# Locked sets / contracts (Wave 0 ships; Wave 1+ asserts against)
# ---------------------------------------------------------------------------

EXPECTED_AGENTS = ("amortization-agent", "refi-npv-agent", "stress-test-agent")
"""Locked agent name set per ROADMAP SC-1 + REQUIREMENTS SUBA-01..03."""

VALID_MODELS = frozenset({"haiku", "sonnet", "opus", "inherit"})
"""Short-alias model whitelist per 11-PATTERNS.md CRITICAL #1a recommendation
(alias over fully-qualified ID so model-class upgrades don't require touching
three agent files)."""

REQUIRED_FRONTMATTER_KEYS = frozenset({"name", "description", "model", "skills"})
"""SUBA-01 contract per ROADMAP SC-1: every agent must declare these keys."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_frontmatter(md_path: Path) -> dict[str, Any]:
    """Parse the YAML frontmatter from a markdown agent file.

    Spec: file starts with the YAML frontmatter delimiter '---' on its own
    line, then the YAML body, then a closing '---' on its own line, then
    the markdown body. Lifted verbatim from 11-PATTERNS.md
    "_parse_frontmatter" pattern (mirrors tests/test_reference/test_schema.py
    YAML-loading idiom).

    Wave 0 ships this helper but does NOT call it (all stubs xfail before
    invocation); Wave 1+ uses it when flipping. Imported lazily inside the
    helper to keep --collect-only fast even if pyyaml grows expensive.

    Args:
        md_path: Path to a markdown file whose first content is YAML
            frontmatter delimited by '---' lines.

    Returns:
        The parsed YAML mapping (a dict) from the frontmatter block.

    Raises:
        ValueError: If the file does not start with the opening '---'
            delimiter, or if the closing '---' delimiter is absent.
    """
    import yaml

    text = md_path.read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"{md_path}: missing opening '---' frontmatter delimiter")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"{md_path}: missing closing '---' frontmatter delimiter")
    return yaml.safe_load(parts[1])  # type: ignore[no-any-return]


# =========================================================================
# SUBA-01 (1 stub) — flipped in Wave 1 (Plan 11-01 ships amortization-agent.md)
# =========================================================================


def test_SUBA_01_amortization_agent_frontmatter_parses_with_required_fields() -> None:
    """SUBA-01 + ROADMAP SC-1: amortization-agent.md frontmatter has model:,
    skills: [mortgage-ops], description, name (matches filename stem)."""
    path = AGENTS_DIR / "amortization-agent.md"
    assert path.exists(), f"SUBA-01: {path} must exist (shipped by Plan 11-01)"
    fm = _split_frontmatter(path)
    missing = REQUIRED_FRONTMATTER_KEYS - fm.keys()
    assert not missing, f"SUBA-01: {path.name} missing frontmatter keys: {missing}"
    assert fm["name"] == "amortization-agent", (
        f"SUBA-01: name={fm['name']!r} must equal 'amortization-agent' (filename stem)"
    )
    assert fm["model"] == "haiku", (
        f"SUBA-01: model={fm['model']!r} must equal 'haiku' "
        "(REQUIREMENTS SUBA-01 + 11-RESEARCH model selection)"
    )
    assert fm["skills"] == ["mortgage-ops"], (
        f"SUBA-01: skills={fm['skills']!r} must equal ['mortgage-ops']"
    )
    description = fm.get("description")
    assert isinstance(description, str), (
        f"SUBA-01: description must be a string, got {type(description).__name__}"
    )
    assert len(description) > 30, (
        f"SUBA-01: description must be a non-trivial routing trigger "
        f"(>30 chars), got {description!r}"
    )


# =========================================================================
# SUBA-02 (1 stub) — flipped in Wave 2 (Plan 11-02 ships refi-npv-agent.md)
# =========================================================================


def test_SUBA_02_refi_npv_agent_frontmatter_model_is_sonnet() -> None:
    """SUBA-02 + ROADMAP SC-4: refi-npv-agent.md frontmatter parses AND
    model=sonnet (Sonnet for multi-step NPV ranking)."""
    path = AGENTS_DIR / "refi-npv-agent.md"
    assert path.exists(), f"SUBA-02: {path} must exist (shipped by Plan 11-02)"
    fm = _split_frontmatter(path)
    missing = REQUIRED_FRONTMATTER_KEYS - fm.keys()
    assert not missing, f"SUBA-02: {path.name} missing frontmatter keys: {missing}"
    assert fm["name"] == "refi-npv-agent", (
        f"SUBA-02: name={fm['name']!r} must equal 'refi-npv-agent' (filename stem)"
    )
    assert fm["model"] == "sonnet", (
        f"SUBA-02: model={fm['model']!r} must equal 'sonnet' "
        "(REQUIREMENTS SUBA-02 + 11-RESEARCH model selection — Sonnet for "
        "multi-step NPV reasoning)"
    )
    assert fm["skills"] == ["mortgage-ops"], (
        f"SUBA-02: skills={fm['skills']!r} must equal ['mortgage-ops']"
    )
    description = fm.get("description")
    assert isinstance(description, str), (
        f"SUBA-02: description must be a string, got {type(description).__name__}"
    )
    assert len(description) > 30, (
        f"SUBA-02: description must be a non-trivial routing trigger "
        f"(>30 chars), got {description!r}"
    )
    # RESEARCH Open Question 1 v1 decision — Write tool intentionally absent
    tools = fm.get("tools") or []
    assert "Write" not in tools, (
        f"SUBA-02: Write tool must NOT be in refi-npv-agent tools list per "
        f"11-RESEARCH.md Open Question 1 v1 decision; got tools={tools}"
    )


# =========================================================================
# SUBA-03 (1 stub) — flipped in Wave 3 (Plan 11-03 ships stress-test-agent.md)
# =========================================================================


def test_SUBA_03_stress_test_agent_frontmatter_model_is_haiku() -> None:
    """SUBA-03 + ROADMAP SC-1 + SC-3 setup: stress-test-agent.md frontmatter
    parses AND model=haiku.

    Model selection LOCKED via Plan 11-03 D-01: Haiku, resolving the SUBA-03
    model-discrepancy surfaced in 11-PATTERNS.md Critical Issue #1a item 2
    (REQUIREMENTS.md says Haiku; orchestrator scratch said TBD; this plan
    locks Haiku per the original requirement and per RESEARCH Architectural
    Responsibility Map — Phase 8 owns the math, this agent only summarizes).
    """
    path = AGENTS_DIR / "stress-test-agent.md"
    assert path.exists(), f"SUBA-03: {path} must exist (shipped by Plan 11-03)"
    fm = _split_frontmatter(path)
    missing = REQUIRED_FRONTMATTER_KEYS - fm.keys()
    assert not missing, f"SUBA-03: {path.name} missing frontmatter keys: {missing}"
    assert fm["name"] == "stress-test-agent", (
        f"SUBA-03: name={fm['name']!r} must equal 'stress-test-agent' (filename stem)"
    )
    assert fm["model"] == "haiku", (
        f"SUBA-03: model={fm['model']!r} must equal 'haiku' "
        "(REQUIREMENTS SUBA-03 + Plan 11-03 LOCKED DECISION D-01 — Haiku for "
        "summarization; Phase 8 owns the math, no multi-step reasoning required)"
    )
    assert fm["skills"] == ["mortgage-ops"], (
        f"SUBA-03: skills={fm['skills']!r} must equal ['mortgage-ops']"
    )
    description = fm.get("description")
    assert isinstance(description, str), (
        f"SUBA-03: description must be a string, got {type(description).__name__}"
    )
    assert len(description) > 30, (
        f"SUBA-03: description must be a non-trivial routing trigger "
        f"(>30 chars), got {description!r}"
    )
    # D-04 — description MUST start with the proactive-dispatch trigger phrase
    # so Claude Code's auto-delegation routes >5-scenario sweeps here without
    # ambiguity.
    assert description.lower().startswith("use proactively for stress sweeps with >5 scenarios"), (
        f"SUBA-03: description must start with 'Use proactively for stress sweeps "
        f"with >5 scenarios' per Plan 11-03 D-04; got: {description[:80]!r}"
    )
    # Write tool MUST be present — needed for the CSV escape hatch (Hard rule
    # #5 + Workflow Step 6 in the agent body); Read+Bash+Write per RESEARCH
    # Code Example 3.
    tools = fm.get("tools") or []
    for required in ("Read", "Bash", "Write"):
        assert required in tools, (
            f"SUBA-03: tools must include {required!r} "
            f"(Write needed for CSV escape hatch); got tools={tools}"
        )


# =========================================================================
# SUBA-04 (3 functions) — flipped in Wave 5 (Plan 11-05)
#   1. test_SUBA_04_skills_field_resolves_for_each_agent (SC-5 smoke,
#      parametrized over EXPECTED_AGENTS)
#   2. test_SUBA_04_refi_handoff_returns_ranked_table (SC-4 refi via
#      transcript fixture)
#   3. test_SUBA_04_amort_handoff_returns_csv_or_markdown (SC-4 amort via
#      transcript fixture)
# =========================================================================


@pytest.mark.parametrize("agent_name", EXPECTED_AGENTS, ids=lambda n: n)
def test_SUBA_04_skills_field_resolves_for_each_agent(agent_name: str) -> None:
    """SUBA-04 + SC-5: each agent's skills field is ['mortgage-ops'] AND the bundled
    scripts are reachable on the filesystem at the skill-resident path.

    Per Plan 11-05 D-04: SC-5 smoke is a pytest-collection-time os.path.exists check.
    Per RESEARCH Pitfall 1, skills: is NOT a script-bundling mechanism — bundled
    scripts are filesystem files reached via Bash. So SC-5 verifies (a) the skills
    frontmatter is correct, (b) the named scripts exist on disk at the path the
    agent body references.
    """
    # Part (a): frontmatter skills field
    path = AGENTS_DIR / f"{agent_name}.md"
    assert path.exists(), f"SUBA-04: {path} must exist (Plans 11-01..11-03 dependency)"
    fm = _split_frontmatter(path)
    assert fm["skills"] == ["mortgage-ops"], (
        f"SUBA-04: {agent_name}.md skills={fm['skills']!r} must equal ['mortgage-ops']"
    )

    # Part (b): bundled scripts reachable at skill-resident path
    skill_scripts_dir = SKILLS_DIR / "scripts"
    expected_script_for = {
        "amortization-agent": "amortize.py",
        "refi-npv-agent": "refi_npv.py",
        "stress-test-agent": "stress_test.py",
    }
    expected_script = expected_script_for[agent_name]
    script_path = skill_scripts_dir / expected_script

    if not skill_scripts_dir.exists():
        pytest.skip(
            f"SUBA-04 SC-5 part (b): {skill_scripts_dir} does not exist yet — Phase 10 "
            f"has not relocated scripts to the skill folder (SKLL-10). Test will pass once "
            f"Phase 10 ships. Skip is intentional cross-phase tolerance per Plan 11-05 D-04."
        )
    assert script_path.exists(), (
        f"SUBA-04 SC-5: {agent_name}.md references {expected_script} but {script_path} "
        f"does not exist on the filesystem (Phase 10 SKLL-10 dependency)."
    )


def test_SUBA_04_refi_handoff_returns_ranked_table() -> None:
    """SUBA-04 + SC-4 (refi): refi-npv-agent output is a ranked markdown table sorted
    descending by NPV (per Plan 11-02 Hard rule #5).

    Tested against the recorded synthetic transcript fixture per Plan 11-05 D-02.
    """
    path = TRANSCRIPT_DIR / "refi_3_offers.transcript.jsonl"
    assert path.exists(), f"SUBA-04 refi: transcript fixture {path} must exist (Plan 11-05 Task 1)"
    lines = [line for line in path.read_text().splitlines() if line.strip()]
    assert len(lines) == 1, f"SUBA-04 refi: expected 1-line transcript, got {len(lines)}"
    content = json.loads(lines[0])["content"]

    # Shape assertion 1: markdown table with lender + NPV columns
    assert "| lender " in content, (
        f"SUBA-04 refi: transcript must contain a markdown table with a 'lender' "
        f"column; got first 200 chars: {content[:200]!r}"
    )
    assert "| NPV " in content, (
        f"SUBA-04 refi: transcript must contain a markdown table with an 'NPV' "
        f"column; got first 200 chars: {content[:200]!r}"
    )
    # Shape assertion 2: at least 3 ranked rows (3-offer fixture; +1 header)
    table_rows = [
        line
        for line in content.splitlines()
        if line.startswith("| ") and "|" in line[2:] and "---" not in line
    ]
    assert len(table_rows) >= 4, (
        f"SUBA-04 refi: expected >=4 table rows (1 header + >=3 data), got {len(table_rows)}"
    )
    # Shape assertion 3: descending-by-NPV ordering — NPV is LAST column per
    # Plan 11-02 Hard rule #5
    npv_values: list[float] = []
    for row in table_rows[1:]:
        cells = [c.strip() for c in row.split("|") if c.strip()]
        npv_str = cells[-1].replace("$", "").replace(",", "")
        npv_values.append(float(npv_str))
    assert npv_values == sorted(npv_values, reverse=True), (
        f"SUBA-04 refi: NPV column must be sorted descending; got {npv_values}"
    )
    # Shape assertion 4: citation discipline (Plans 11-02 + 11-03)
    assert "Computed by:" in content, (
        "SUBA-04 refi: transcript must contain a 'Computed by:' citation marker"
    )
    assert "refi_npv.py" in content, (
        "SUBA-04 refi: transcript must reference refi_npv.py in the 'Computed by:' citation"
    )


def test_SUBA_04_amort_handoff_returns_csv_or_markdown() -> None:
    """SUBA-04 + SC-4 (amort): amortization-agent output is a markdown table OR a CSV path
    string under reports/{NNN}-amortization-{YYYY-MM-DD}.csv (per Plan 11-01 Hard rule #4).
    """
    path = TRANSCRIPT_DIR / "amort_single_loan.transcript.jsonl"
    assert path.exists(), f"SUBA-04 amort: transcript fixture {path} must exist (Plan 11-05 Task 1)"
    lines = [line for line in path.read_text().splitlines() if line.strip()]
    assert len(lines) == 1, f"SUBA-04 amort: expected 1-line transcript, got {len(lines)}"
    content = json.loads(lines[0])["content"]

    has_markdown_table = "| period " in content and "| balance " in content
    has_csv_path = bool(re.search(r"reports/\d{3}-amortization-\d{4}-\d{2}-\d{2}\.csv", content))
    assert has_markdown_table or has_csv_path, (
        f"SUBA-04 amort: transcript must contain EITHER a markdown table "
        f"(|period|date|payment|principal|interest|balance| per amortization-agent.md:66) "
        f"OR a CSV path (reports/NNN-amortization-YYYY-MM-DD.csv); got: {content[:200]!r}"
    )
    assert "Computed by:" in content, (
        "SUBA-04 amort: transcript must contain a 'Computed by:' citation marker"
    )
    assert "amortize.py" in content, (
        "SUBA-04 amort: transcript must reference amortize.py in the 'Computed by:' citation"
    )


# =========================================================================
# SUBA-05 (1 stub) — flipped in Wave 4 (Plan 11-04 lands modes/stress.md routing rule)
# =========================================================================


def test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent() -> None:
    """SUBA-05 + ROADMAP SC-2: modes/stress.md documents the >5 scenario dispatch rule.

    Per Plan 11-04 LOCKED DECISION D-01: threshold is strictly >5 (matches the literal SC-2
    text); D-02: cross-phase update protocol (this branch executed because Phase 10 had
    shipped at task time).
    """
    import re

    stress_md_path = SKILLS_DIR / "modes" / "stress.md"
    assert stress_md_path.exists(), (
        f"SUBA-05: {stress_md_path} must exist (Phase 10 SKLL-05 dependency); "
        "if Phase 10 has not yet shipped, see .planning/phases/11-subagents/11-04-SUBA-05-TODO.md"
    )
    stress_md = stress_md_path.read_text()
    # Regex matches phrasings: "scenarios > 5", "more than 5 scenarios",
    # "scenario_count > 5" — pinned by an explicit positive assertion.
    pattern = re.compile(
        r"(scenarios?\s*(>|more than|greater than)\s*5|scenario[_ ]count\s*>\s*5).*"
        r"(stress-test-agent|subagent)",
        re.IGNORECASE | re.DOTALL,
    )
    assert pattern.search(stress_md), (
        "SUBA-05: modes/stress.md must document 'sweeps with > 5 scenarios route to stress-test-agent' "
        "per the insertion contract in .planning/phases/11-subagents/11-04-SUBA-05-TODO.md"
    )
    # SKILL.md cross-reference assertion — Phase 10 surface MUST cite the agent name
    # so the routing breadcrumb is followable from SKILL.md → modes/stress.md → agent file.
    skill_md = (SKILLS_DIR / "SKILL.md").read_text()
    assert "stress-test-agent" in skill_md, (
        "SUBA-05: SKILL.md must cross-reference stress-test-agent in its routing block "
        "(per Plan 11-04 SKILL.md insertion contract)"
    )


# =========================================================================
# SUBA-06 (1 stub) — flipped in Wave 5 (Plan 11-05 ships transcript + count_tokens call)
# =========================================================================


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason=(
        "SC-3 SUBA-06 token-budget test requires ANTHROPIC_API_KEY for "
        "anthropic.count_tokens (FREE — no content billing per Anthropic docs — "
        "but requires network round-trip). Skip is intentional for local dev "
        "without the key; CI must inject the key as a secret."
    ),
)
def test_SUBA_06_stress_summary_under_1000_tokens() -> None:
    """SC-3: 50-scenario rate-shock summary fits under 1,000 tokens.

    Per Plan 11-05 D-01: tokenizer = anthropic.Anthropic().messages.count_tokens (the
    official Claude tokenizer; tiktoken explicitly REJECTED per RESEARCH Standard Stack
    because it is OpenAI-specific and ~5-20% drift on the <1k boundary).

    Per Plan 11-05 D-03: budget threshold is exactly 1000 tokens (response.input_tokens
    < 1000) — not 999, not 1001. Matches the literal SC-3 wording.

    Per Plan 11-05 D-02: tested against the synthetic transcript fixture (committed at
    tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl) for CI
    determinism. Live capture for nightly eval is documented in the fixture README but
    NOT run in CI.
    """
    anthropic = pytest.importorskip("anthropic")
    path = TRANSCRIPT_DIR / "stress_50_scenarios.transcript.jsonl"
    assert path.exists(), f"SC-3: transcript fixture {path} must exist (Plan 11-05 Task 1)"
    content = json.loads(path.read_text().strip().splitlines()[0])["content"]

    client = anthropic.Anthropic()
    response = client.messages.count_tokens(
        model="claude-haiku-4-5",
        messages=[{"role": "assistant", "content": content}],
    )
    assert response.input_tokens < 1000, (
        f"SC-3 SUBA-06: stress-test-agent summary returned {response.input_tokens} tokens, "
        f"exceeds 1000-token budget (Plan 11-05 D-03 threshold; ROADMAP SC-3 verbatim). "
        f"To diagnose: drop a highlight row or shorten the narrative in the fixture, OR if "
        f"the agent output legitimately requires >1000 tokens, surface as a Phase 12 follow-up."
    )
