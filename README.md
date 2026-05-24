# mortgage-ops

Private underwriting workbench for household mortgage decisions. It combines deterministic mortgage math, citation-backed eligibility predicates, household state, property ingestion, and report generation into reproducible GO / WATCH / NO-GO decisions. The LLM is a router and narrator, never an arithmetic owner.

See `.planning/PROJECT.md` for full context, `.planning/ROADMAP.md` for the phase plan, and `CLAUDE.md` for non-negotiable conventions (Decimal money, Pydantic v2, mypy --strict, ruff, pytest).

## Quick start

```bash
uv sync --locked              # install pinned deps
uv run pre-commit install     # wire local hooks
uv run pytest                 # run tests
uv run mypy --strict .        # typecheck
uv run ruff check .           # lint
```
