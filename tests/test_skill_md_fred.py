"""Phase 12 Wave-3 live tests: LIVE-02 closed via Pattern A prose-only injection per D-12-LIVE02-01.

Plan 12-03 adds the static `## Live Mortgage Rates` section to
.claude/skills/mortgage-ops/SKILL.md per D-12-LIVE02-01 Pattern A (prose-only
injection with cache-file references). Tests assert verbatim heading,
required token references (MORTGAGE30US, MORTGAGE15US, data/cache/fred_*.json,
scripts/fred_cli.py), and that the SKILL.md does NOT use the
`!`...`` shell-injection syntax (Anthropic Claude Code support uncertain per
12-RESEARCH.md Open Question 1).

Wave-0 xfails were flipped to passing in Plan 12-03 Wave 3.

Requirements covered:
  - LIVE-02 + D-12-LIVE02-01: `## Live Mortgage Rates` heading exists
  - LIVE-02 + D-12-LIVE02-01: both series + cache paths + script cited
  - D-12-LIVE02-01: no `!`...`` shell-injection syntax in SKILL.md
  - SKLL-01/SKLL-02 inheritance: token + line budgets preserved after Phase 12 insert
  - D-12-LIVE02-01: section appears BEFORE `## Math Discipline`
"""

from __future__ import annotations

import re
from pathlib import Path

SKILL_MD: Path = (
    Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops" / "SKILL.md"
)


def test_skill_md_has_live_mortgage_rates_heading() -> None:
    """LIVE-02 + D-12-LIVE02-01: SKILL.md MUST contain the exact heading
    `## Live Mortgage Rates`."""
    body = SKILL_MD.read_text()
    assert "## Live Mortgage Rates" in body


def test_skill_md_cites_both_series_and_cache_paths() -> None:
    """LIVE-02 + D-12-LIVE02-01: prose-only injection (Pattern A) must reference
    all four strings. Forbidden: `!`...`` shell-injection syntax (Open Q1
    unresolved)."""
    body = SKILL_MD.read_text()
    for required in (
        "MORTGAGE30US",
        "MORTGAGE15US",
        "data/cache/fred_",
        "scripts/fred_cli.py",
    ):
        assert required in body, f"SKILL.md missing required token {required!r}"


def test_skill_md_does_not_use_shell_injection_syntax() -> None:
    """D-12-LIVE02-01: Pattern A (prose-only) MUST NOT use the `!`...`` shell-injection
    form since Anthropic skill-shell-injection support is uncertain (Open Q1).

    Anchored to the presence of the new `## Live Mortgage Rates` heading so the
    absence-check is meaningful (not vacuously true on an empty/wrong file).
    """
    body = SKILL_MD.read_text()
    # Anchor: the section must exist before this absence-check is meaningful.
    assert "## Live Mortgage Rates" in body, (
        "Plan 12-03 has not shipped the FRED section yet; "
        "shell-injection guard is not yet load-bearing."
    )
    # WR-03 broadening: D-12-LIVE02-01 forbids ALL `!`...`` shell-injection
    # syntax (not just the fred-mentioning variant). A future edit introducing
    # `!`bash scripts/foo.sh`` (no fred mention) must also fail this guard.
    # The negative-lookbehind `(?<![\\])` skips escaped `\!` so prose can
    # discuss the syntax safely.
    forbidden = re.findall(r"(?<![\\])!`[^`\n]+`", body)
    assert not forbidden, f"forbidden shell-injection syntax in SKILL.md: {forbidden}"


def test_skill_md_token_budget_after_phase12_insert() -> None:
    """Phase 10 SKILL.md ships at ~3419 tokens; Phase 12 adds ~80 tokens.
    Budget enforced: ≤ 4500 cl100k tokens (SKLL-01 inherited; D-02 10% safety
    margin under the 5000 Anthropic-spec hard cap)."""
    from tests._skill_helpers import count_tokens

    body = SKILL_MD.read_text()
    token_count = count_tokens(body)
    assert token_count <= 4500, (
        f"SKILL.md token budget breached: {token_count} > 4500 "
        f"(SKLL-01 + D-02 10% safety margin under 5000 Anthropic spec)"
    )


def test_skill_md_line_budget_after_phase12_insert() -> None:
    """SKLL-02 inherited: ≤ 500 lines. Phase 12 adds ~14 lines → ~271 lines total."""
    lines = SKILL_MD.read_text().splitlines()
    assert len(lines) <= 500, f"SKILL.md line budget breached: {len(lines)} > 500"


def test_skill_md_section_appears_before_math_discipline() -> None:
    """D-12-LIVE02-01 positioning: `## Live Mortgage Rates` must precede `## Math Discipline`
    to keep the routing-block-relative neighborhood intact (SKLL-02 inheritance)."""
    body = SKILL_MD.read_text()
    live_idx = body.index("## Live Mortgage Rates")
    math_idx = body.index("## Math Discipline")
    assert live_idx < math_idx, "`## Live Mortgage Rates` must precede `## Math Discipline`"


def test_skill_md_references_table_includes_fred_context() -> None:
    """Plan 12-08: SKILL.md references table MUST point at references/fred-context.md
    with trigger phrases for current-rate / FRED / MORTGAGE30US questions."""
    body = SKILL_MD.read_text()
    assert "references/fred-context.md" in body, (
        "SKILL.md missing references/fred-context.md row in topic-to-reference table"
    )
    # Trigger phrases must appear nearby (within the references-table region)
    table_start = body.find("Loading Additional Context")
    table_end = body.find("## Number Formatting", table_start)
    table_region = body[table_start:table_end]
    for trigger in ("FRED", "MORTGAGE30US"):
        assert trigger in table_region, (
            f"SKILL.md references-table region missing trigger phrase {trigger!r}"
        )


def test_fred_context_reference_doc_has_required_sections() -> None:
    """Plan 12-08: references/fred-context.md MUST have 6 numbered sections per
    arm-mechanics.md template + Citation Index appendix."""
    doc_path = (
        Path(__file__).resolve().parent.parent
        / ".claude"
        / "skills"
        / "mortgage-ops"
        / "references"
        / "fred-context.md"
    )
    body = doc_path.read_text()
    required_headings = [
        "## 1. HTTP API (canonical path",
        "## 2. MCP Server (optional secondary path",
        "## 3. Cache Schema",
        "## 4. SKILL.md Routing Rule",
        "## 5. Eval Harness Integration",
        "## 6. Pitfalls",
        "## Appendix: Citation Index",
    ]
    for heading in required_headings:
        assert heading in body, f"references/fred-context.md missing required heading: {heading!r}"
