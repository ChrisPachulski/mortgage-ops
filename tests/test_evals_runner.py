"""Phase 12 Wave-0 stubs for evals/runner.py — EVAL-01..03 + D-12-SC4-01 gate.

Plan 12-04 ships HarnessReport + three-bucket aggregator (pass | fail | skip
per D-12-SC4-01). Plan 12-05 ships 22 prompt files (21 mode-coverage + 1
live-rate-injection per D-12-SC1-01). Plan 12-06 pairs every prompt with an
oracle JSON file (EVAL-02).

All tests in this module are decorated `@pytest.mark.xfail(strict=True)`.

Requirements covered:
  - EVAL-01 + D-12-SC1-01: 22 prompts total (21 mode-coverage + 1 live-rate-injection)
  - SC-5: every one of 7 modes has >=1 prompt
  - EVAL-02: every prompt has a paired oracle
  - EVAL-03 + D-12-SC4-01: three-bucket gate denominator excludes numeric_skip
  - D-12-SC4-01: TBD prompts surface as SKIP, not PASS
"""

from __future__ import annotations

from pathlib import Path

import pytest

EVALS_DIR: Path = Path(__file__).resolve().parent.parent / "evals"
PROMPTS_DIR: Path = EVALS_DIR / "prompts"
EXPECTED_DIR: Path = EVALS_DIR / "expected"

ALL_MODES = (
    "evaluate",
    "compare",
    "refinance",
    "affordability",
    "stress",
    "amortize",
    "arm",
)
"""SC-5: every mode in the v1 prompt set must have >=1 prompt."""


@pytest.mark.xfail(
    reason=(
        "Plan 12-05 ships 22 prompts (21 mode-coverage + 1 live-rate-injection "
        "per D-12-SC1-01) — EVAL-01"
    ),
    strict=True,
)
def test_evals_prompts_dir_has_22_prompts() -> None:
    """EVAL-01 + D-12-SC1-01: 22 prompts total. 21 mode-coverage (3 x 7) + 1
    live-rate-injection."""
    md_files = [p for p in PROMPTS_DIR.glob("*.md") if p.stem != ".gitkeep"]
    assert len(md_files) == 22, f"expected 22 prompts, got {len(md_files)}"


@pytest.mark.xfail(
    reason="Plan 12-05 ships prompts grouped by mode — SC-5",
    strict=True,
)
@pytest.mark.parametrize("mode", ALL_MODES)
def test_each_mode_has_at_least_one_prompt(mode: str) -> None:
    """SC-5: every one of 7 modes must have >=1 prompt with `mode: {name}` frontmatter."""
    import frontmatter  # type: ignore[import-untyped]

    matches = []
    for p in PROMPTS_DIR.glob("*.md"):
        if p.stem == ".gitkeep":
            continue
        fm = frontmatter.load(p)
        if fm.metadata.get("mode") == mode:
            matches.append(p.stem)
    assert matches, f"no prompts for mode {mode!r}"


@pytest.mark.xfail(
    reason="Plan 12-06 pairs every prompt with its oracle — EVAL-02",
    strict=True,
)
def test_every_prompt_has_paired_oracle() -> None:
    """EVAL-02: every evals/prompts/{id}.md has a evals/expected/{id}.json
    (1:1 by stem)."""
    prompts = [p for p in PROMPTS_DIR.glob("*.md") if p.stem != ".gitkeep"]
    # Anchor the xfail until Plan 12-05 ships the prompt set — otherwise the
    # empty loop below would vacuously pass and trigger XPASS(strict).
    assert prompts, f"no prompts present yet in {PROMPTS_DIR}"
    for prompt in prompts:
        oracle = EXPECTED_DIR / f"{prompt.stem}.json"
        assert oracle.is_file(), f"missing oracle for {prompt.stem}: {oracle}"


@pytest.mark.xfail(
    reason=(
        "Plan 12-04 ships HarnessReport with three-bucket gate per "
        "D-12-SC4-01 — EVAL-03"
    ),
    strict=True,
)
def test_gate_passes_with_13_anchored_pass_and_9_skip() -> None:
    """D-12-SC4-01: 13/(13+0) = 100% >= 95% — gate PASSES (with 9 TBD skipped)."""
    from evals.runner import HarnessReport  # type: ignore[import-not-found]

    report = HarnessReport(
        n_prompts=22,
        route_match_count=22,
        numeric_pass_count=13,
        numeric_fail_count=0,
        numeric_skip_count=9,
        failures=[],
    )
    assert report.numeric_match_rate == 1.0
    assert report.numeric_match_rate >= 0.95


@pytest.mark.xfail(
    reason="Plan 12-04 ships HarnessReport — D-12-SC4-01 fail case",
    strict=True,
)
def test_gate_fails_with_one_anchored_fail_among_13() -> None:
    """D-12-SC4-01: 12/(12+1) = 92.3% < 95% — gate FAILS."""
    from evals.runner import HarnessReport

    report = HarnessReport(
        n_prompts=22,
        route_match_count=22,
        numeric_pass_count=12,
        numeric_fail_count=1,
        numeric_skip_count=9,
        failures=[],
    )
    assert report.numeric_match_rate < 0.95
    # Specifically: pass / (pass + fail) — skip excluded from denominator
    assert abs(report.numeric_match_rate - (12.0 / 13.0)) < 1e-9


@pytest.mark.xfail(
    reason="Plan 12-04 ships score_numeric_match — D-12-SC4-01 skip semantics",
    strict=True,
)
def test_tbd_prompt_reported_as_skipped_not_passed() -> None:
    """D-12-SC4-01: a prompt with numeric_status='skip' must be reported as SKIP
    (not PASS)."""
    from evals.metrics import (  # type: ignore[import-not-found]
        NumericScore,
        score_numeric_match,
    )

    expected = {
        "numeric_status": "skip",
        "defer_until_phase": "13.0",
        "expected_numbers": [],
    }
    score = score_numeric_match(
        model_response="any text",
        expected=expected,
        subprocess_calls=[],
    )
    assert score == NumericScore.SKIP
