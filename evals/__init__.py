"""Phase 12 eval harness package.

Top-level package for the deterministic eval harness. Wave 0 (Plan 12-00)
ships this empty `__init__.py` plus `.gitkeep` seams under prompts/,
expected/, and runs/. Later waves populate:

- `evals.runner` (Plan 12-04): HarnessReport dataclass + transcript replay
  loop. Three-bucket gate (pass | fail | skip) per D-12-SC4-01.
- `evals.metrics` (Plan 12-04): NumericScore enum + score_numeric_match +
  score_route_match + STDOUT-only detect_hallucinations per D-12-SC3-01.
- `evals/prompts/*.md` (Plan 12-05): 22 prompt files (21 mode-coverage +
  1 live-rate-injection) per D-12-SC1-01.
- `evals/expected/*.json` (Plan 12-06): one oracle JSON per prompt.
- `evals/runs/` (System Layer per DATA_CONTRACT.md): eval-runner output
  target; gitignored except the `.gitkeep` seam.
"""
