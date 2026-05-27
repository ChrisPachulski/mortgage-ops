"""Phase 15 Plan 15-01 Wave 0 RED stubs for skill routing introspection.

Covers MODE-01 (property mode-file presence + extractor prompt embed) and
MODE-02 (SKILL.md token-budget + cross-reference + Row 0 routing presence).

Filesystem-introspection tests targeting:
  - ``.claude/skills/mortgage-ops/SKILL.md`` (existing; Plan 15-04 inserts Row 0)
  - ``.claude/skills/mortgage-ops/modes/property.md`` (NEW; Plan 15-04 ships)

Per LOCKED DECISION D-02 (Phase 10): token-budget assertion uses
``tests._skill_helpers.count_tokens`` (tiktoken cl100k_base) with a 10% safety
margin against the 5000-token Anthropic spec; effective threshold = 4500
cl100k tokens.

modes/property.md is unbuilt until Plan 15-04 — those tests are individually
xfailed via a missing-file guard at fixture / per-test level so the file
collects cleanly. Token-budget + Row 0 tests against SKILL.md run unconditionally
and currently RED because Plan 15-04 has not yet inserted Row 0 (the existing
SKILL.md doesn't mention zillow.com or property_analyze.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._skill_helpers import count_tokens

# ---------------------------------------------------------------------------
# Skill root + property-mode-file paths.
# ---------------------------------------------------------------------------

SKILL_ROOT_PATH: Path = (
    Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops"
)


@pytest.fixture
def skill_root() -> Path:
    """Path to .claude/skills/mortgage-ops/ — entry point for all
    filesystem-introspection tests in this module."""
    return SKILL_ROOT_PATH


PROPERTY_MODE_FILE = SKILL_ROOT_PATH / "modes" / "property.md"


def _xfail_unless_property_mode_exists() -> pytest.MarkDecorator:
    """Per-test xfail decorator applied to assertions that require
    modes/property.md (unbuilt until Plan 15-04). When the file exists,
    the decorator is inert and the assertion runs for real."""
    return pytest.mark.xfail(
        condition=not PROPERTY_MODE_FILE.exists(),
        reason="Wave 1/2 — modes/property.md not yet shipped (Plan 15-04)",
        strict=False,
    )


# ---------------------------------------------------------------------------
# MODE-02 — SKILL.md token budget (Pitfall 1)
# ---------------------------------------------------------------------------


def test_skill_md_token_budget(skill_root: Path) -> None:
    """MODE-02 + Pitfall 1 + LOCKED D-02: SKILL.md ≤ 4500 cl100k tokens
    AFTER Plan 15-04 Row 0 insertion. tiktoken cl100k_base undercounts the
    Anthropic tokenizer by ~10-15%; the 4500 threshold encodes the safety
    margin against the 5000-token spec recommendation."""
    skill_md = (skill_root / "SKILL.md").read_text()
    n_tokens = count_tokens(skill_md)
    assert n_tokens <= 4500, (
        f"SKILL.md is {n_tokens} cl100k tokens (budget 4500 = 5000 Anthropic "
        f"spec - 10% safety margin per D-02 / Pitfall 1). Phase 15 Row 0 "
        f"insertion overflowed; trim references table per Phase 10 deferred "
        f"recovery (PATTERNS L812 token-budget guard)."
    )


# ---------------------------------------------------------------------------
# MODE-01 + D-15-ROUTE-01 — Row 0 (Zillow URL pin) routing presence
# ---------------------------------------------------------------------------


def test_property_mode_row0_present(skill_root: Path) -> None:
    """MODE-01 + D-15-ROUTE-01: SKILL.md routing table includes Row 0 for
    zillow.com URL substring + 'analyze listing' phrase trigger. Per SKLL-02
    + D-12 (Phase 10), load-bearing routing must appear in the first 200
    lines so the routing table survives Anthropic context compaction."""
    skill_md = (skill_root / "SKILL.md").read_text()
    head = "\n".join(skill_md.splitlines()[:200])
    assert "zillow.com" in head, (
        "Row 0 (D-15-ROUTE-01) missing 'zillow.com' substring trigger in SKILL.md first 200 lines"
    )
    assert "analyze listing" in head, (
        "Row 0 (D-15-ROUTE-01) missing 'analyze listing' phrase trigger in SKILL.md first 200 lines"
    )
    assert "property" in head, (
        "Row 0 (D-15-ROUTE-01) missing 'property' mode reference in SKILL.md first 200 lines"
    )
    assert "property_analyze.py" in head, (
        "Row 0 (D-15-ROUTE-01) missing 'property_analyze.py' script reference "
        "in SKILL.md first 200 lines"
    )


def test_points_mode_route_present(skill_root: Path) -> None:
    """Discount-points questions must route deterministically to points_breakeven.py."""
    skill_md = (skill_root / "SKILL.md").read_text()
    head = "\n".join(skill_md.splitlines()[:200])
    assert "discount points" in head
    assert "points_breakeven.py" in head
    assert (skill_root / "modes" / "points.md").is_file()


# ---------------------------------------------------------------------------
# MODE-01 — modes/property.md presence + cross-reference
# ---------------------------------------------------------------------------


def test_property_mode_file_exists(skill_root: Path) -> None:
    """MODE-01: .claude/skills/mortgage-ops/modes/property.md is a real file
    on disk. Plan 15-04 ships this; until then, the test is xfailed by the
    module-level guard."""
    property_mode = skill_root / "modes" / "property.md"
    assert property_mode.is_file(), (
        f"MODE-01: modes/property.md not found at {property_mode}; "
        f"Plan 15-04 (Wave 2) ships this file"
    )


def test_skill_md_cross_references_property_mode(skill_root: Path) -> None:
    """MODE-02: SKILL.md cross-references the new property mode (either via
    explicit 'modes/property.md' path or via 'property' routing keyword in
    the mode-routing table). The progressive-disclosure pattern (D-09)
    requires SKILL.md → modes/*.md hand-off be discoverable."""
    skill_md = (skill_root / "SKILL.md").read_text()
    assert ("modes/property.md" in skill_md) or ("property" in skill_md), (
        "SKILL.md does not cross-reference modes/property.md (MODE-02 + D-09 "
        "progressive disclosure)"
    )


# ---------------------------------------------------------------------------
# MODE-01 — modes/property.md content invariants (extractor prompt,
# _shared.md load-first, orchestrator dispatch, error code enumeration)
# ---------------------------------------------------------------------------


@_xfail_unless_property_mode_exists()
def test_property_mode_contains_extractor_prompt(skill_root: Path) -> None:
    """MODE-01 + RESEARCH Pattern 1: modes/property.md embeds the WebFetch +
    __NEXT_DATA__ JSON extractor prompt verbatim so Claude's mode body can
    transform raw Zillow HTML into a PropertyListing JSON tempfile."""
    body = (skill_root / "modes" / "property.md").read_text()
    assert "__NEXT_DATA__" in body, (
        "modes/property.md missing '__NEXT_DATA__' extractor anchor (MODE-01 + RESEARCH Pattern 1)"
    )
    assert "WebFetch" in body, (
        "modes/property.md missing 'WebFetch' tool invocation reference "
        "(MODE-01 + RESEARCH Pattern 1)"
    )


@_xfail_unless_property_mode_exists()
def test_property_mode_loads_shared_first(skill_root: Path) -> None:
    """MODE-01 + Phase 10 D-09 + D-10: modes/property.md instructs Claude to
    load modes/_shared.md FIRST (standard convention all mode files honor)."""
    body = (skill_root / "modes" / "property.md").read_text()
    assert "modes/_shared.md" in body, (
        "modes/property.md missing 'modes/_shared.md' load-first reference "
        "(Phase 10 D-09 / D-10 convention)"
    )
    assert "FIRST" in body, (
        "modes/property.md does not flag _shared.md as 'FIRST' load (Phase 10 D-09 convention)"
    )


@_xfail_unless_property_mode_exists()
def test_property_mode_dispatches_to_orchestrator(skill_root: Path) -> None:
    """MODE-01 + RESEARCH OQ2 RESOLVED: modes/property.md contains a worked
    example invocation that calls
    'python .claude/skills/mortgage-ops/scripts/property_analyze.py'
    (full skill-relative path; matches Phase 13 property_fetch.py precedent)."""
    body = (skill_root / "modes" / "property.md").read_text()
    expected = "python .claude/skills/mortgage-ops/scripts/property_analyze.py"
    assert expected in body, (
        f"modes/property.md missing orchestrator dispatch example {expected!r} "
        f"(MODE-01 + RESEARCH OQ2 RESOLVED full skill-relative path)"
    )


@_xfail_unless_property_mode_exists()
def test_property_mode_documents_envelope_codes(skill_root: Path) -> None:
    """MODE-01 + PATTERNS L79 (edge-cases convention): modes/property.md
    enumerates the orchestrator's error envelope codes so Claude can narrate
    each failure mode against _shared.md §Error Narration Template."""
    body = (skill_root / "modes" / "property.md").read_text()
    expected_codes = [
        "household_yaml_invalid",
        "profile_yaml_invalid",
        "listing_validation_failed",
        "fred_cache_cold",
        "output_dir_unwritable",
    ]
    for code in expected_codes:
        assert code in body, (
            f"modes/property.md does not document envelope error code {code!r} "
            f"(MODE-01 + PATTERNS L79 edge-cases convention)"
        )


@_xfail_unless_property_mode_exists()
def test_property_mode_fred_cache_recovery_uses_real_cli_shape(skill_root: Path) -> None:
    body = (skill_root / "modes" / "property.md").read_text()
    assert "fred_cli.py\n  MORTGAGE30US --latest" in body
    assert "fred_cli.py\n  get MORTGAGE30US --latest" not in body
