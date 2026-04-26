# mortgage-ops

Personal-use mortgage analysis: deterministic Python calc engine + Claude skill frontend. Math correctness first — every dollar figure traces to a tested, deterministic Python function. The LLM is a router and narrator, never an arithmetic owner.

See `.planning/PROJECT.md` for full context, `.planning/ROADMAP.md` for the phase plan, and `CLAUDE.md` for non-negotiable conventions (Decimal money, Pydantic v2, mypy --strict, ruff, pytest).

## Quick start

```bash
uv sync --locked              # install pinned deps
uv run pre-commit install     # wire local hooks
uv run pytest                 # run tests
uv run mypy --strict .        # typecheck
uv run ruff check .           # lint
```
