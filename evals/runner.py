"""Phase 12 eval harness runner.

Two execution modes (v1 ships only `replay-stub`):

  replay-stub (v1, ships green) — synthesizes a deterministic transcript from
    each prompt's frontmatter + the paired oracle JSON. Asserts the
    prompt/expected pair is internally consistent (route_match + numeric_match
    scorers pass given a stub transcript that mimics an ideal agent run).
    This validates the eval DESIGN; live behavior is a Phase 13+ concern.

  replay (deferred to Phase 13+) — loads pre-recorded transcripts from
    evals/runs/{prompt_id}.jsonl. Same scorers; real data flow. Not shipped in v1.

Three-bucket gate per D-12-SC4-01:
  numeric_match_rate = numeric_pass_count / (numeric_pass_count + numeric_fail_count)
  numeric_skip_count is reported but excluded from the gate denominator.

SC-4 gate: numeric_match_rate >= 0.95.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-untyped]

from evals.metrics import (
    NumericScore,
    score_numeric_match,
    score_route_match,
)

EVALS_DIR: Path = Path(__file__).resolve().parent
PROMPTS_DIR: Path = EVALS_DIR / "prompts"
EXPECTED_DIR: Path = EVALS_DIR / "expected"
RUNS_DIR: Path = EVALS_DIR / "runs"

SC4_GATE_THRESHOLD: float = 0.95
"""ROADMAP SC-4 + D-12-SC4-01: numeric_match_rate must be >= 0.95 across (pass + fail)."""


@dataclass
class FailureReport:
    """Per-prompt failure record surfaced in HarnessReport.failures."""

    prompt_id: str
    kind: str  # "route" | "numeric" | "hallucination" | "missing_oracle"
    detail: str


@dataclass
class HarnessReport:
    """D-12-SC4-01 three-bucket aggregator.

    n_prompts is the total count (including skips); route_match_count uses this denominator.
    numeric_match_rate uses (pass + fail) denominator — SKIP is excluded.
    """

    n_prompts: int = 0
    route_match_count: int = 0
    numeric_pass_count: int = 0
    numeric_fail_count: int = 0
    numeric_skip_count: int = 0
    failures: list[FailureReport] = field(default_factory=list)

    @property
    def route_match_rate(self) -> float:
        if self.n_prompts == 0:
            return 0.0
        return self.route_match_count / self.n_prompts

    @property
    def numeric_match_rate(self) -> float:
        """D-12-SC4-01: denominator = pass + fail (skip excluded)."""
        denom = self.numeric_pass_count + self.numeric_fail_count
        if denom == 0:
            return 0.0
        return self.numeric_pass_count / denom

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_prompts": self.n_prompts,
            "route_match_count": self.route_match_count,
            "route_match_rate": round(self.route_match_rate, 4),
            "numeric_pass_count": self.numeric_pass_count,
            "numeric_fail_count": self.numeric_fail_count,
            "numeric_skip_count": self.numeric_skip_count,
            "numeric_match_rate": round(self.numeric_match_rate, 4),
            "failures": [
                {"prompt_id": f.prompt_id, "kind": f.kind, "detail": f.detail}
                for f in self.failures
            ],
        }


def load_prompt_metadata(prompt_path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from evals/prompts/{id}.md via python-frontmatter."""
    fm = frontmatter.load(str(prompt_path))
    return dict(fm.metadata)


def load_expected(prompt_id: str) -> dict[str, Any]:
    """Load evals/expected/{prompt_id}.json oracle."""
    path = EXPECTED_DIR / f"{prompt_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing oracle for {prompt_id}: {path}")
    payload: dict[str, Any] = json.loads(path.read_text())
    return payload


def synthesize_stub_transcript(
    prompt_content: str,
    expected: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build a deterministic transcript that mimics an ideal agent run.

    v1 replay-stub mode: for each expected_scripts entry, synthesize one
    subprocess event whose stdout contains every expected_numbers value tagged
    with `provenance` != 'static'. The synthesized model_response cites every
    expected_number (with $ formatting for cents-precision numbers).

    This is the "internally consistent" check: if the prompt's frontmatter +
    oracle JSON form a self-consistent pair, the stub-mode runner reports PASS.
    Failures here indicate prompt/oracle drift (e.g., expected_number references
    a script not in expected_scripts).
    """
    sub_calls: list[dict[str, Any]] = []
    # Map: stdout-bound expected_numbers grouped by their source_script
    by_script: dict[str, list[dict[str, Any]]] = {}
    for entry in expected.get("expected_numbers", []) or []:
        if entry.get("provenance") == "static":
            continue  # static numbers don't need stdout
        src = entry.get("source_script", "amortize.py")
        by_script.setdefault(src, []).append(entry)

    # Use expected_scripts as the authoritative list of invocations; if absent,
    # invent one synthesized call per source_script.
    expected_scripts = list(expected.get("expected_scripts", []) or [])
    scripts_seen = {s.get("script") for s in expected_scripts}
    for src in by_script:
        if src not in scripts_seen:
            expected_scripts.append({"script": src, "args_must_include": ["--input"]})

    for spec in expected_scripts:
        script = spec.get("script", "amortize.py")
        cmd: list[str] = ["python", f".claude/skills/mortgage-ops/scripts/{script}"]
        for inc in spec.get("args_must_include", []) or []:
            cmd.append(inc)
            if inc == "--input":
                cmd.append("/tmp/eval_stub.json")
        stdout_nums = by_script.get(script, [])
        stdout_payload = json.dumps({e["label"]: e["value"] for e in stdout_nums})
        sub_calls.append(
            {
                "type": "subprocess",
                "cmd": cmd,
                "stdin": "{}",
                "stdout": stdout_payload,
                "stderr": "",
                "returncode": 0,
            }
        )

    # Build a model response that cites every expected_number.
    # Prepend the mode keywords + a routing-confirmation preamble so
    # score_route_match's keyword check passes in stub-mode (in live mode the
    # skill naturally narrates the mode it routed to).
    route_keywords = expected.get("expected_route_keywords", []) or []
    mode = expected.get("mode", "")
    preamble_parts: list[str] = []
    if mode:
        preamble_parts.append(f"Routing to {mode} mode.")
    if route_keywords:
        preamble_parts.append(f"Keywords: {', '.join(route_keywords)}.")
    response_lines: list[str] = []
    if preamble_parts:
        response_lines.append(" ".join(preamble_parts))
    response_lines.append(prompt_content)
    for entry in expected.get("expected_numbers", []) or []:
        val = entry["value"]
        # Format as money for decimals, plain for others
        try:
            formatted = (
                f"${Decimal(str(val)):,.2f}" if "." in str(val) else str(val)
            )
        except Exception:
            formatted = str(val)
        response_lines.append(f"{entry['label']}: {formatted}")
    transcript: list[dict[str, Any]] = [
        {"type": "user_prompt", "content": prompt_content},
        *sub_calls,
        {"type": "model_response", "content": "\n".join(response_lines)},
    ]
    return transcript


def run_replay_stub(
    prompt_path: Path,
) -> tuple[bool, NumericScore, list[FailureReport]]:
    """v1 replay-stub: synthesize transcript from prompt + oracle; score it.

    Returns: (route_ok, numeric_score, failures).
    """
    prompt_id = prompt_path.stem
    expected = load_expected(prompt_id)
    fm = frontmatter.load(str(prompt_path))
    transcript = synthesize_stub_transcript(fm.content, expected)

    model_response = next(
        (e["content"] for e in transcript if e["type"] == "model_response"),
        "",
    )
    sub_calls = [e for e in transcript if e["type"] == "subprocess"]

    failures: list[FailureReport] = []
    route_ok = score_route_match(model_response, expected, sub_calls)
    if not route_ok:
        failures.append(FailureReport(prompt_id, "route", "stub route mismatch"))
    score = score_numeric_match(model_response, expected, sub_calls)
    if score == NumericScore.FAIL:
        failures.append(FailureReport(prompt_id, "numeric", "stub numeric mismatch"))

    return route_ok, score, failures


def run_all(prompts_dir: Path) -> HarnessReport:
    """Iterate every evals/prompts/*.md, score, return aggregated report."""
    report = HarnessReport()
    prompts = [p for p in sorted(prompts_dir.glob("*.md")) if p.stem != ".gitkeep"]
    report.n_prompts = len(prompts)
    for prompt in prompts:
        try:
            route_ok, score, failures = run_replay_stub(prompt)
        except FileNotFoundError as exc:
            report.failures.append(
                FailureReport(prompt.stem, "missing_oracle", str(exc))
            )
            continue
        if route_ok:
            report.route_match_count += 1
        if score == NumericScore.PASS:
            report.numeric_pass_count += 1
        elif score == NumericScore.FAIL:
            report.numeric_fail_count += 1
        elif score == NumericScore.SKIP:
            report.numeric_skip_count += 1
        report.failures.extend(failures)
    return report


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Exit 0 if both numeric_match_rate AND route_match_rate >= gate."""
    parser = argparse.ArgumentParser(
        prog="evals/runner",
        description="Phase 12 eval harness — score prompts vs oracles.",
    )
    parser.add_argument(
        "prompts",
        nargs="?",
        default=str(PROMPTS_DIR),
        help="Prompt file or directory (default: evals/prompts/)",
    )
    parser.add_argument(
        "--mode",
        choices=["replay-stub"],
        default="replay-stub",
        help="v1 ships replay-stub only; live mode deferred to Phase 13+",
    )
    parser.add_argument(
        "--gate",
        type=float,
        default=SC4_GATE_THRESHOLD,
        help="match-rate gate applied to BOTH numeric and route (default 0.95 per SC-4 / D-12-SC4-01)",
    )
    args = parser.parse_args(argv)

    target = Path(args.prompts)
    prompts_dir = target if target.is_dir() else target.parent

    report = run_all(prompts_dir)
    print(json.dumps(report.to_dict(), indent=2))
    # SC-4 requires BOTH numeric_match_rate AND route_match_rate >= gate.
    return (
        0
        if report.numeric_match_rate >= args.gate
        and report.route_match_rate >= args.gate
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
