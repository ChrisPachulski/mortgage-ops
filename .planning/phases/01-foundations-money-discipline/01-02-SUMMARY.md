---
phase: 01-foundations-money-discipline
plan: 02
status: complete
requirements:
  - FND-07
completed_date: 2026-04-26
---

# Phase 01 Plan 02: Data Contract + User-Layer Schema Skeletons — Summary

Authored the four-layer (User / System / Data / Reference) `DATA_CONTRACT.md` at repo root and committed two redacted User-Layer schema skeletons (`config/household.example.yml`, `config/profile.example.yml`). The spec Plan 06 must enforce — gitignore + `scripts/hooks/block-user-layer.py` + CI re-run — is now in place; the User-Layer path list is the single source of truth Plan 06's `USER_LAYER_PATTERNS` tuple has to mirror verbatim. The Wave-1 phase gate (`uv run ruff check . && uv run ruff format --check . && uv run mypy --strict . && uv run pytest`) still exits 0.

## Status

**COMPLETE.** All `must_haves.truths` verified. All `must_haves.artifacts` exist with the required `contains` substrings and minimum line counts. All `must_haves.key_links` patterns match. Both planned tasks executed and committed atomically. Plan executed exactly as written — zero deviations.

## Files Created

| Path | Purpose | Lines |
|------|---------|-------|
| `DATA_CONTRACT.md` | Four-layer data contract (User / System / Data / Reference) with explicit per-layer path tables; cites `scripts/hooks/block-user-layer.py` as the enforcement mechanism Plan 06 will ship | 75 |
| `config/household.example.yml` | System-Layer redacted skeleton documenting `household.yml` schema (location, applicants[], monthly_debts, current_housing_payment); all values are placeholder zeros / sentinel strings | 35 |
| `config/profile.example.yml` | System-Layer redacted skeleton documenting `profile.yml` schema (display, defaults, modes); all values are obvious placeholders | 28 |

## Files Modified

None — all three artifacts are net-new. The existing `config/.gitkeep` from Plan 01-01 was deliberately left in place (the live `config/household.yml` is User-Layer and never committed, so the seam still earns its keep).

## Commits Made

| SHA | Subject |
|-----|---------|
| `6fb7265` | `docs(01): add four-layer DATA_CONTRACT.md` |
| `5e6be15` | `chore(01): add redacted User Layer YAML skeletons` |

(A third commit will land for this SUMMARY.md per `commit_docs: true`.)

## User Layer Path List (canonical — Plan 06 must mirror verbatim)

The User Layer table in `DATA_CONTRACT.md` enumerates exactly these paths. Plan 06's `scripts/hooks/block-user-layer.py` MUST construct its `USER_LAYER_PATTERNS` and `USER_LAYER_GLOB_DIRS` tuples from this list — drift between the two will fail Plan 06's acceptance criteria (PATTERNS.md Convention 6, line 379).

| Path | Glob? | Notes for Plan 06 |
|------|-------|-------------------|
| `config/household.yml` | exact | The committed `config/household.example.yml` is **System Layer** — do not block it |
| `config/profile.yml` | exact | The committed `config/profile.example.yml` is **System Layer** — do not block it |
| `modes/_profile.md` | exact | Phase 10 — does not exist yet, but the hook should still match the path |
| `data/mortgage-ops.duckdb` | exact | Phase 9 — also a Data-Layer file (both rules apply) |
| `data/mortgage-ops.duckdb-wal` | exact | DuckDB WAL sidecar |
| `data/mortgage-ops.duckdb-shm` | exact | DuckDB shared-memory sidecar |
| `reports/*.md` | glob (with `reports/.gitkeep` whitelisted) | Phase 10+ — `.gitkeep` must remain trackable |

The `data/reference/.gitkeep` and `reports/.gitkeep` seam files are explicitly **whitelisted** (`!path/.gitkeep`) so the seam directories remain in git even after Plan 06 ignores their contents.

## System Layer vs User Layer (the diff that prevents PII leaks)

This plan ships the committed **example** YAML files. The **live** YAML files do not exist yet and must never be committed:

| File | Layer | This plan ships? | Plan 06 enforcement |
|------|-------|------------------|---------------------|
| `config/household.example.yml` | System | Yes (committed) | None — System Layer files are normal commits |
| `config/profile.example.yml` | System | Yes (committed) | None — System Layer files are normal commits |
| `config/household.yml` | User | **No** — must not exist | `.gitignore` entry + `block-user-layer.py` pattern |
| `config/profile.yml` | User | **No** — must not exist | `.gitignore` entry + `block-user-layer.py` pattern |

Verified via `test ! -f config/household.yml && test ! -f config/profile.yml` — neither live file exists at the close of this plan.

## Must-Haves Verification

### `must_haves.truths`

| Truth | Result |
|-------|--------|
| `DATA_CONTRACT.md` declares all four layers (User / System / Data / Reference) with explicit path lists | **PASS** — `grep -c '^## .* Layer' DATA_CONTRACT.md` returns `4`; each layer section contains a `\| Path \| Purpose \|` table |
| `config/household.example.yml` exists as a redacted skeleton with no real PII | **PASS** — file exists, all numeric values are `"0.00"` strings or `0` sentinels, ZIP is `"00000"`, names are `"Applicant A"` / `"Applicant B"` |
| `config/profile.example.yml` exists as a redacted skeleton with no real PII | **PASS** — file exists, only schema-shape values present (e.g., `"USD"`, `"percent"`, `360`); no preferences, no identity |
| `DATA_CONTRACT.md` cites `scripts/hooks/block-user-layer.py` as the enforcement mechanism | **PASS** — `grep -c 'block-user-layer\.py' DATA_CONTRACT.md` returns `2` (once in the enumerated enforcement list, once in Layer Cross-References) |

### `must_haves.artifacts`

| Path | `contains` substring | `min_lines` | Result |
|------|----------------------|-------------|--------|
| `DATA_CONTRACT.md` | `## User Layer` | 50 | **PASS** — substring present once; file is 75 lines |
| `config/household.example.yml` | `household:` | (none specified) | **PASS** — substring present at top-level key |
| `config/profile.example.yml` | `profile:` | (none specified) | **PASS** — substring present at top-level key |

### `must_haves.key_links`

| From | To | Pattern | Result |
|------|-----|---------|--------|
| `DATA_CONTRACT.md` | `scripts/hooks/block-user-layer.py` | `block-user-layer\.py` | **PASS** — 2 matches |
| `DATA_CONTRACT.md` | `.gitignore` (User-Layer overlap) | `config/household\.yml` | **PASS** — 2 matches |

### Task-level `<verify>` automated commands

Both task verify commands exit 0 verbatim:

- **Task 1:** `test -f DATA_CONTRACT.md && grep -q '^# Data Contract$' ... && [ "$(wc -l < DATA_CONTRACT.md)" -ge 50 ]` → **PASS**
- **Task 2:** `test -f config/household.example.yml && test -f config/profile.example.yml && grep -q '^household:$' ... && uv run python -c "import yaml; yaml.safe_load(...)"` → **PASS** (YAML parses; top-level keys verified: `household` → `[location, applicants, monthly_debts, current_housing_payment]`, `profile` → `[display, defaults, modes]`, `applicants` is a list of length 2)

### Wave-1 Phase Gate (from `<verification>`)

`uv run ruff check . && uv run ruff format --check . && uv run mypy --strict . && uv run pytest` — **all four sub-commands exit 0**. The added YAML files are not in scope for ruff/mypy (validated by `yaml.safe_load`); the added markdown is not in scope for any of the four. The phase gate is preserved per Wave-1 invariant (PATTERNS.md Convention 9).

## Deviations from Plan

**None — plan executed exactly as written.**

The plan's literal `<action>` content for all three files was committed verbatim (modulo the YAML files being parsed by `yaml.safe_load` to confirm well-formedness). No auto-fixes applied; no missing critical functionality detected; no blockers encountered.

## Authentication Gates

None.

## Threat Flags

None — no new security-relevant surface introduced beyond the plan's `<threat_model>` already enumerated. T-1-05, T-1-06, T-1-07 mitigations all shipped:

- **T-1-05 / T-1-06 (Information Disclosure on example YAMLs):** All numeric placeholders are `"0.00"` strings, ZIP is `"00000"`, credit_score is `0`, names are `"Applicant A"` / `"Applicant B"`. Both files start with a comment block containing `COMMITTED SKELETON` and reference `DATA_CONTRACT.md`. No real PII anywhere.
- **T-1-07 (Tampering — DATA_CONTRACT.md drift vs hook source):** The User-Layer path list section above is the canonical reference. Plan 06's hook task explicitly reads `DATA_CONTRACT.md` before authoring `USER_LAYER_PATTERNS` — drift is detected at Plan 06 acceptance time, not silently.
- **T-1-08 (DATA_CONTRACT.md itself):** Disposition was `accept` — the spec is meant to be public-readable; verified that the document contains zero real user values.

## Forward References for Plan 06 to Satisfy

Plan 06 (Pre-commit Hook + .gitignore + CI) inherits these obligations from this plan's text:

1. **`.gitignore` entries** must include each User Layer path enumerated in `DATA_CONTRACT.md` (with the seam-file whitelist):
   ```
   config/household.yml
   config/profile.yml
   modes/_profile.md
   data/mortgage-ops.duckdb
   data/mortgage-ops.duckdb-wal
   data/mortgage-ops.duckdb-shm
   reports/*.md
   !reports/.gitkeep
   data/market/*.parquet
   data/reference/*  # No — Reference Layer is committed; this line should NOT exist
   !data/reference/.gitkeep
   ```
   (Caveat: `data/reference/*` is **Reference Layer** — committed. Only the duckdb / reports / market paths are gitignored on the data side.)

2. **`scripts/hooks/block-user-layer.py`** must construct `USER_LAYER_PATTERNS` and `USER_LAYER_GLOB_DIRS` from the User Layer table in `DATA_CONTRACT.md`. The hook MUST refuse `git add -f` bypasses (i.e., reject staged paths regardless of `.gitignore` status).

3. **CI workflow** (`.github/workflows/ci.yml`) must re-run `block-user-layer.py` against the staged tree as a server-side check (defense against `git commit --no-verify`).

4. **`.pre-commit-config.yaml`** must register the `block-user-layer.py` hook as a local hook with `stages: [pre-commit]`.

## Self-Check: PASSED

- All committed files exist and are tracked:
  - `DATA_CONTRACT.md` (75 lines, all four layer headings, cites `block-user-layer.py`)
  - `config/household.example.yml` (35 lines, valid YAML, top-level `household:` with 4 sub-keys)
  - `config/profile.example.yml` (28 lines, valid YAML, top-level `profile:` with 3 sub-keys)
- Both commits present in `git log`: `6fb7265` (DATA_CONTRACT.md), `5e6be15` (example YAMLs)
- Wave-1 phase gate (`ruff check . && ruff format --check . && mypy --strict . && pytest`) exits 0
- Live User-Layer files (`config/household.yml`, `config/profile.yml`) confirmed absent
- Pre-existing seam files (`config/.gitkeep` from Plan 01-01) preserved
