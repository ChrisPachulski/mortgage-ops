# Data Contract

This document defines which files belong to the **User Layer** (read-only from system code), the **System Layer** (auto-updatable code & instructions), the **Data Layer** (generated artifacts), and the **Reference Layer** (committed regulatory data, manually refreshed).

The contract is enforced by:

1. `.gitignore` — blocks `git add` for User Layer and Data Layer paths.
2. `scripts/hooks/block-user-layer.py` (pre-commit hook, see `.pre-commit-config.yaml`) — refuses any commit that stages a User Layer path, including `git add -f` bypasses of `.gitignore`.
3. CI re-runs the same hook (server-side belt-and-suspenders for `--no-verify` bypasses).

## User Layer (NEVER auto-updated; gitignored)

These files contain personal data, customizations, and computed user-private state. **No system process — pre-commit hooks, CI, scripts, or future Claude skills — may write to a User Layer path.** Runtime enforcement is each script's responsibility; commit-time enforcement is the pre-commit hook + `.gitignore`.

| Path | Purpose |
|------|---------|
| `config/household.yml` | Household income, applicants, joint-applicant credit scores, monthly debts, location |
| `config/profile.yml` | User identity, preferences (mortgage display conventions, default loan term, etc.) |
| `modes/_profile.md` | (Phase 10) user-specific narrative overrides for the Claude skill |
| `data/mortgage-ops.duckdb` | (Phase 9) computed scenarios + reports |
| `data/mortgage-ops.duckdb-wal` | (Phase 9) DuckDB write-ahead log sidecar |
| `data/mortgage-ops.duckdb-shm` | (Phase 9) DuckDB shared-memory sidecar |
| `reports/*.md` | (Phase 10+) generated reports — except `reports/.gitkeep`, which seams the directory |

**Rule:** User Layer files are *read* by system code (e.g., `lib/affordability.py` will read `config/household.yml` in Phase 4) but are *never written* by system code. Annual data refresh is a manual user action (edit `config/household.yml` by hand).

## System Layer (auto-updatable; committed)

| Path | Purpose |
|------|---------|
| `lib/**` | Python calc engine (Phases 1–8) |
| `scripts/**` | CLI helpers (Phase 3+) and tooling hooks (Phase 1) |
| `tests/**` | Test suite + fixtures |
| `pyproject.toml` / `uv.lock` / `.python-version` | Build + deps |
| `.github/workflows/**` | CI |
| `.pre-commit-config.yaml` | Hook config |
| `CLAUDE.md` / `DATA_CONTRACT.md` / `README.md` | Project docs |
| `config/household.example.yml` / `config/profile.example.yml` | Schema skeletons (no real values) |
| `orchestration/**` | (Phase 9) Node DuckDB writer + lockfile |
| `.claude/skills/mortgage-ops/**` | (Phase 10) skill bundle (excluding `modes/_profile.md`) |
| `.claude/agents/**` | (Phase 11) subagent definitions |
| `evals/**` | (Phase 12) eval harness |

System Layer files are auto-updatable by Claude / scripts / CI. Commits to these paths are the normal flow.

## Data Layer (generated; gitignored)

| Path | Purpose |
|------|---------|
| `data/mortgage-ops.duckdb` | (Phase 9) single-file persistence — also a User Layer file by virtue of containing user-private scenarios |
| `data/market/*.parquet` | (Phase 12) FRED rate cache |
| `reports/{###}-{slug}-{YYYY-MM-DD}.md` | (Phase 10+) generated reports |

**Rule:** Data Layer files are regenerated from System Layer code + User Layer inputs + Reference Layer YAMLs. They are never hand-edited; an out-of-band edit will be overwritten by the next regeneration. The DuckDB file is also enumerated in the User Layer because it contains user-private numeric state — both layer rules apply (gitignored AND blocker rejects `git add -f`).

## Reference Layer (committed; manually refreshed annually)

| Path | Purpose |
|------|---------|
| `data/reference/conforming-limits-{YEAR}.yml` | (Phase 2) FHFA baseline + ceiling + per-county lookup |
| `data/reference/fha-limits-{YEAR}.yml` | (Phase 2) FHA floor/ceiling + per-county lookup |
| `data/reference/fha-mip-rates.yml` | (Phase 2) FHA UFMIP + annual MIP per term/LTV/loan-amount tier |
| `data/reference/va-funding-fees.yml` | (Phase 2) VA funding fee tables |
| `data/reference/va-residual-income.yml` | (Phase 2) VA residual income geographic × family-size table |
| `data/reference/usda-income-limits.yml` | (Phase 2) USDA 115%-of-area-median thresholds |
| `data/reference/irs-pub936.yml` | (Phase 2) IRS Pub 936 mortgage interest deduction caps |
| `data/known-loans.yml` | (Phase 9) product catalog |

**Rule:** Reference Layer files are committed and human-readable; each must include `source:` (URL of the regulatory page) and `effective:` (ISO-8601 date). Annual refresh = YAML edit + commit, never code change. A startup-time staleness check (Phase 2) warns when `effective:` is > 12 months old.

## Layer Cross-References

- The User Layer paths in this document must match the `USER_LAYER_PATTERNS` and `USER_LAYER_GLOB_DIRS` tuples in `scripts/hooks/block-user-layer.py` exactly. Both lists are kept in sync by editing this file and the hook source in the same commit.
- The User Layer paths must also be enumerated in `.gitignore`. The seam files (`reports/.gitkeep`, `data/reference/.gitkeep`) are explicitly whitelisted (`!path/.gitkeep`) so the seam directories remain tracked.
- Phase 1 commits this contract and the empty `data/reference/` directory (with `.gitkeep`); Reference Layer YAML files are added in Phase 2.
