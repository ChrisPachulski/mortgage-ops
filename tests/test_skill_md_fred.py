"""Phase 12 Wave-0 stubs for SKILL.md FRED injection — LIVE-02 + D-12-LIVE02-01.

Plan 12-03 adds the static `## Live Mortgage Rates` section to
.claude/skills/mortgage-ops/SKILL.md per D-12-LIVE02-01 Pattern A (prose-only
injection with cache-file references). Tests assert verbatim heading,
required token references (MORTGAGE30US, MORTGAGE15US, data/cache/fred_*.json,
scripts/fred_cli.py), and that the SKILL.md does NOT use the
`!`...`` shell-injection syntax (Anthropic Claude Code support uncertain per
12-RESEARCH.md Open Question 1).

All tests in this module are decorated `@pytest.mark.xfail(strict=True)`.

Requirements covered:
  - LIVE-02 + D-12-LIVE02-01: `## Live Mortgage Rates` heading exists
  - LIVE-02 + D-12-LIVE02-01: both series + cache paths + script cited
  - D-12-LIVE02-01: no `!`...`` shell-injection syntax in SKILL.md
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILL_MD: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude" / "skills" / "mortgage-ops" / "SKILL.md"
)


@pytest.mark.xfail(
    reason="Plan 12-03 adds `## Live Mortgage Rates` section per D-12-LIVE02-01",
    strict=True,
)
def test_skill_md_has_live_mortgage_rates_heading() -> None:
    """LIVE-02 + D-12-LIVE02-01: SKILL.md MUST contain the exact heading
    `## Live Mortgage Rates`."""
    body = SKILL_MD.read_text()
    assert "## Live Mortgage Rates" in body


@pytest.mark.xfail(
    reason="Plan 12-03 cites both series + cache paths + script — D-12-LIVE02-01",
    strict=True,
)
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


@pytest.mark.xfail(
    reason="Plan 12-03 prose-only — D-12-LIVE02-01 forbids `!`...` `` syntax",
    strict=True,
)
def test_skill_md_does_not_use_shell_injection_syntax() -> None:
    """D-12-LIVE02-01: Pattern A (prose-only) MUST NOT use the `!`...`` shell-injection
    form since Anthropic skill-shell-injection support is uncertain (Open Q1).

    Anchored to the presence of the new `## Live Mortgage Rates` heading so the
    xfail does not vacuously pass before Plan 12-03 ships the section.
    """
    body = SKILL_MD.read_text()
    # Anchor: the section must exist before this absence-check is meaningful.
    # Until Plan 12-03 ships the heading, this assertion forces the xfail.
    assert "## Live Mortgage Rates" in body, (
        "Plan 12-03 has not shipped the FRED section yet; "
        "shell-injection guard is not yet load-bearing."
    )
    # Match the specific shell-injection pattern: literal !` followed by a command
    # mentioning fred (in prose, backtick-code-spans are fine; only the inline-shell
    # form is forbidden).
    forbidden = re.findall(r"!`[^`]*fred[^`]*`", body, flags=re.IGNORECASE)
    assert not forbidden, f"forbidden shell-injection syntax in SKILL.md: {forbidden}"
