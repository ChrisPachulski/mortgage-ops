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

import os
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
# SUBA-04 (1 stub, parametrized over 3 agents in Wave 5) — flipped in Wave 5
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-05 parametrizes")
def test_SUBA_04_each_agent_skills_field_is_mortgage_ops() -> None:
    """SUBA-04 + ROADMAP SC-5: every agent declares
    `skills: [mortgage-ops]` (Phase 10 dependency — the named skill must
    exist on disk under `.claude/skills/mortgage-ops/`).

    Wave 5 (Plan 11-05) will replace this body with a parametrize over
    `EXPECTED_AGENTS`, calling `_split_frontmatter` on each agent file
    and asserting `fm["skills"] == ["mortgage-ops"]`.
    """
    pytest.fail("Wave 0 stub")


# =========================================================================
# SUBA-05 (1 stub) — flipped in Wave 4 (Plan 11-04 lands modes/stress.md routing rule)
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-04 routing rule")
def test_SUBA_05_stress_mode_routes_sweeps_over_5_to_subagent() -> None:
    """SUBA-05 + ROADMAP SC-2: modes/stress.md documents the routing rule
    'sweeps with > 5 scenarios route to stress-test-agent'.

    Wave 4 (Plan 11-04) will flip this stub by inserting the routing
    paragraph into modes/stress.md (Phase 10 owned file) and replacing
    this body with a regex assertion against the file contents.
    """
    pytest.fail("Wave 0 stub")


# =========================================================================
# SUBA-06 (1 stub) — flipped in Wave 5 (Plan 11-05 ships transcript + count_tokens call)
# =========================================================================


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — Plan 11-05 ships fixture + count_tokens")
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason=(
        "SUBA-06 token-budget test requires ANTHROPIC_API_KEY (count_tokens is FREE "
        "but requires the key per platform.claude.com/docs/en/build-with-claude/token-counting)"
    ),
)
def test_SUBA_06_stress_summary_under_1k_tokens() -> None:
    """SUBA-06 + ROADMAP SC-3: 50-scenario rate-shock summary fits under 1000 tokens.

    Uses anthropic.Anthropic().messages.count_tokens(model='claude-haiku-4-5', ...)
    against tests/fixtures/subagent_transcripts/stress_50_scenario_summary.md.
    Alternative tokenizers (OpenAI's BPE in particular) are explicitly REJECTED
    per 11-RESEARCH.md — they are OpenAI-specific and drift on the order of
    20 percent against the actual Claude tokenizer, which would mask real
    overages on a 1000-token budget.

    Wave 5 (Plan 11-05) will flip this stub by:
      1. Authoring tests/fixtures/subagent_transcripts/stress_50_scenario_summary.md
      2. Calling client.messages.count_tokens with role=assistant
      3. Asserting response.input_tokens < 1000
    """
    pytest.fail("Wave 0 stub")
