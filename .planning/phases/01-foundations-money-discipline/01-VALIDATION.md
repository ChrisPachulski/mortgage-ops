---
phase: 1
slug: foundations-money-discipline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-26
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (+ mypy --strict, ruff) |
| **Config file** | `pyproject.toml` (Wave 1 installs) |
| **Quick run command** | `uv run pytest tests/ -x --tb=short` |
| **Full suite command** | `uv run pytest && uv run mypy --strict . && uv run ruff check .` |
| **Estimated runtime** | ~10 seconds (Phase 1 has no math; just model + fixture loaders) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --tb=short`
- **After every plan wave:** Run `uv run pytest && uv run mypy --strict . && uv run ruff check .`
- **Before `/gsd-verify-work`:** Full suite must be green AND CI must be green on a pushed branch
- **Max feedback latency:** 30 seconds local; ≤ 5 minutes CI

---

## Per-Task Verification Map

> Filled in during execution as plans land. Each task in each PLAN.md must map to one row here. Planner is responsible for emitting per-task `<automated>` verify commands; this file tracks the rollup.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _TBD_   | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Phase 1 is itself the Wave-0 phase for the project — it installs the test framework, lints, type-checker, and CI. The "Wave 0 stubs" concept rolls up into the Wave 1 task that creates `pyproject.toml` and the bare `tests/` skeleton.

- [ ] `pyproject.toml` exists with pytest, mypy, ruff dev deps + tool config
- [ ] `tests/conftest.py` — shared fixtures (golden-fixture loader)
- [ ] `tests/fixtures/` — pinned JSON for the four FND-09 oracles
- [ ] `tests/test_smoke.py` — minimal smoke test so CI has something green to run on first commit

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub Actions blocks merges on red CI | FND-06 | Branch-protection setting lives outside the repo | After CI runs once, in repo settings enable "Require status checks to pass before merging" with the Phase 1 workflow as required |
| Pre-commit hook fires on user-layer files | FND-10 | Requires a fresh `git commit` against a real working tree | After install: `touch config/household.yml && git add -f config/household.yml && git commit -m test` should be rejected |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers `pyproject.toml` + `tests/conftest.py` + `tests/fixtures/`
- [ ] No watch-mode flags (`--watch`, `-f`) — CI is non-interactive
- [ ] Feedback latency < 30s local
- [ ] `nyquist_compliant: true` set in frontmatter once planner fills the per-task table

**Approval:** pending
