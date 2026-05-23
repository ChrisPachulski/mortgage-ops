"""Phase 12 Wave-6 + Plan 15-05 complete: 23 prompts + 23 oracles + three-bucket gate end-to-end.

Plan 12-04 shipped HarnessReport + three-bucket aggregator (pass | fail | skip
per D-12-SC4-01). Plan 12-05 shipped 22 prompt files (21 mode-coverage + 1
live-rate-injection per D-12-SC1-01) and flipped the 22-count + per-mode xfails.
Plan 12-06 ships 22 paired oracle JSON files (EVAL-02) and flips the final xfail.
Plan 15-05 adds the 23rd prompt (property-analysis-01) closing ROADMAP SC-6;
the per-mode coverage list stays at the 7 Phase 12 modes (property is a Phase
15 mode added on top, not part of the SC-5 7-mode invariant).

0 tests xfailed in this module — Wave 0..6 all green end-to-end.

Requirements covered:
  - EVAL-01 + D-12-SC1-01: 23 prompts total (21 mode-coverage + 1 live-rate-injection + 1 property-analysis)
  - SC-5: every one of 7 Phase 12 modes has >=1 prompt
  - EVAL-02: every prompt has a paired oracle (1:1 by stem)
  - EVAL-03 + D-12-SC4-01: three-bucket gate denominator excludes numeric_skip
  - D-12-SC4-01: TBD prompts surface as SKIP, not PASS
  - SC-6: property-analysis-01 prompt exercises full property mode end-to-end
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


def test_evals_prompts_dir_has_23_prompts() -> None:
    """EVAL-01 + D-12-SC1-01 + ROADMAP SC-6: 23 prompts total. 21 mode-coverage
    (3 x 7) + 1 live-rate-injection (Plan 12-05) + 1 property-analysis (Plan
    15-05). Phase 12 baseline was 22; Plan 15-05 adds property-analysis-01.md
    against the Phase 15 synthetic SFH fixture to close ROADMAP SC-6."""
    md_files = [p for p in PROMPTS_DIR.glob("*.md") if p.stem != ".gitkeep"]
    assert len(md_files) == 23, f"expected 23 prompts, got {len(md_files)}"


@pytest.mark.parametrize("mode", ALL_MODES)
def test_each_mode_has_at_least_one_prompt(mode: str) -> None:
    """SC-5: every one of 7 modes must have >=1 prompt with `mode: {name}` frontmatter.
    Flipped from xfail by Plan 12-05."""
    import frontmatter  # type: ignore[import-untyped,import-not-found,unused-ignore]

    matches = []
    for p in PROMPTS_DIR.glob("*.md"):
        if p.stem == ".gitkeep":
            continue
        fm = frontmatter.load(p)
        if fm.metadata.get("mode") == mode:
            matches.append(p.stem)
    assert matches, f"no prompts for mode {mode!r}"


def test_every_prompt_has_paired_oracle() -> None:
    """EVAL-02: every evals/prompts/{id}.md has a evals/expected/{id}.json
    (1:1 by stem). Flipped from xfail by Plan 12-06."""
    prompts = [p for p in PROMPTS_DIR.glob("*.md") if p.stem != ".gitkeep"]
    assert prompts, f"no prompts present in {PROMPTS_DIR}"
    for prompt in prompts:
        oracle = EXPECTED_DIR / f"{prompt.stem}.json"
        assert oracle.is_file(), f"missing oracle for {prompt.stem}: {oracle}"


def test_gate_passes_with_13_anchored_pass_and_9_skip() -> None:
    """D-12-SC4-01: 13/(13+0) = 100% >= 95% — gate PASSES (with 9 TBD skipped)."""
    from evals.runner import HarnessReport

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


def test_tbd_prompt_reported_as_skipped_not_passed() -> None:
    """D-12-SC4-01: a prompt with numeric_status='skip' must be reported as SKIP
    (not PASS)."""
    from evals.metrics import (
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


def test_runner_main_fails_loudly_on_single_file_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """WR-05 regression: passing a single ``.md`` file used to silently
    expand to its parent directory and re-score all prompts in it. v1
    fails loudly via ``parser.error()`` (exit 2 + stderr message).
    Single-file scoring is deferred to v1.1."""
    from evals.runner import main

    fake_prompt = tmp_path / "fake.md"
    fake_prompt.write_text("---\nmode: evaluate\n---\nbody")
    with pytest.raises(SystemExit) as excinfo:
        main([str(fake_prompt)])
    # argparse's ``parser.error`` raises SystemExit(2)
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "single-file scoring not supported" in captured.err
