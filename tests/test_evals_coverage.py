"""Phase 12 Wave-6 citation-coverage + end-to-end gate tests.

These three tests close ROADMAP SC-3 + SC-4 + SC-5 at the integration layer:

- test_every_stdout_provenance_has_existing_source_script — SC-3 cross-check that every
  anchored expected_number with provenance="stdout" cites a script that EXISTS in the
  skill bundle. Defends against oracle drift after Phase 10+ script-relocations.
- test_prompt_mode_matches_oracle_mode — schema consistency: prompt mode field MUST
  equal oracle mode field (Plan 12-05 + Plan 12-06 author them in parallel; this
  test pins the contract).
- test_runner_gate_passes_on_v1_set — SC-4 + D-12-SC4-01 + SC-6 end-to-end:
  `evals.runner.run_all` on the shipped 23-prompt set (22 Phase-12 prompts +
  1 Phase-15 property-analysis-01) produces 14 pass / 0 fail / 9 skip,
  gate at 100% >= 95%.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-untyped,import-not-found,unused-ignore]
import pytest
from evals.runner import EXPECTED_DIR, PROMPTS_DIR, run_all

SKILL_SCRIPTS_DIR: Path = (
    Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops" / "scripts"
)


def _all_oracles() -> list[dict[str, Any]]:
    """Load every oracle JSON under evals/expected/ as parsed dicts."""
    return [json.loads(p.read_text()) for p in sorted(EXPECTED_DIR.glob("*.json"))]


def test_every_stdout_provenance_has_existing_source_script() -> None:
    """SC-3: every anchored expected_number with provenance='stdout' MUST cite a script
    that exists under .claude/skills/mortgage-ops/scripts/. Defends against oracle drift."""
    failures: list[str] = []
    for oracle in _all_oracles():
        if oracle.get("numeric_status") != "anchored":
            continue
        for entry in oracle.get("expected_numbers", []) or []:
            if entry.get("provenance") != "stdout":
                continue
            src = entry.get("source_script", "")
            if not src:
                failures.append(f"{oracle['id']}: expected_number missing source_script")
                continue
            script_path = SKILL_SCRIPTS_DIR / src
            if not script_path.is_file():
                failures.append(f"{oracle['id']}: source_script {src!r} not found at {script_path}")
    assert not failures, "\n".join(failures)


def test_prompt_mode_matches_oracle_mode() -> None:
    """Schema consistency: prompt.mode == oracle.mode (1:1 paired by stem)."""
    failures: list[str] = []
    for prompt_path in sorted(PROMPTS_DIR.glob("*.md")):
        if prompt_path.stem == ".gitkeep":
            continue
        oracle_path = EXPECTED_DIR / f"{prompt_path.stem}.json"
        prompt_mode = frontmatter.load(prompt_path).metadata.get("mode")
        oracle_mode = json.loads(oracle_path.read_text()).get("mode")
        if prompt_mode != oracle_mode:
            failures.append(
                f"{prompt_path.stem}: prompt mode={prompt_mode!r}, oracle mode={oracle_mode!r}"
            )
    assert not failures, "\n".join(failures)


def test_runner_gate_passes_on_v1_set() -> None:
    """SC-4 + D-12-SC4-01 + SC-6 end-to-end: 14 anchored pass + 0 fail + 9 skip
    -> gate 100% >= 95%. Plan 15-05 added property-analysis-01 (numeric_status=
    anchored, 3 anchored numerics) so the pass count grew from 13 to 14; skip
    + fail counts are unchanged."""
    report = run_all(PROMPTS_DIR)
    assert report.n_prompts == 23, f"expected 23 prompts, got {report.n_prompts}"
    assert report.numeric_pass_count == 14, (
        f"expected 14 pass, got {report.numeric_pass_count} "
        f"(fail={report.numeric_fail_count}, skip={report.numeric_skip_count}, "
        f"failures={report.failures})"
    )
    assert report.numeric_fail_count == 0, (
        f"expected 0 fail, got {report.numeric_fail_count}; failures: {report.failures}"
    )
    assert report.numeric_skip_count == 9, f"expected 9 skip, got {report.numeric_skip_count}"
    assert report.numeric_match_rate == pytest.approx(1.0), (
        f"expected gate at 1.0, got {report.numeric_match_rate}"
    )
    assert report.numeric_match_rate >= 0.95, "SC-4 gate breached"
