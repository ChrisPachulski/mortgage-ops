# Dependency review

This document covers how `mortgage-ops` keeps its third-party dependencies
fresh, safe, and license-compliant. It is the runbook companion to
`scripts/audit-deps.sh` and `.github/workflows/audit.yml`.

## Cadence

| Activity                            | Owner          | Cadence    |
|-------------------------------------|----------------|------------|
| Python dependency version review    | Repo maintainer| Quarterly  |
| Node dependency version review      | Repo maintainer| Quarterly  |
| Security audit (`audit-deps.sh`)    | GitHub Actions | Weekly     |
| License review (new additions)      | Repo maintainer| At PR time |

The "quarterly" cadence applies to *upgrading* dependencies (minor / patch
roll-ups, picking up new major versions). The "weekly" cadence applies to
*detecting* newly disclosed vulnerabilities in the versions already pinned.

The scheduled audit runs Mondays at 14:00 UTC (09:00 / 10:00 US Eastern,
depending on DST). It is also runnable on demand via the **Actions →
Audit → Run workflow** button.

## Running the audit locally

```bash
bash scripts/audit-deps.sh
```

Exit code:

* `0` — no High or Critical vulnerabilities (Low / Moderate may still print
  as warnings).
* `1` — one or more High or Critical vulnerabilities found, after applying
  the ignore lists hardcoded at the top of the script (see "Known
  exceptions" below).

The script runs three tools and prints each under a clear header:

1. `uv run pip-audit --strict` — Python vulnerability scan. Audits a
   `uv pip freeze --exclude-editable` snapshot so the editable
   `mortgage-ops` project itself is skipped (it is unpublished).
2. `npm audit --omit=dev` — Node vulnerability scan, production deps only.
3. `uv run pip-licenses --format=json --order=license` — Python license
   inventory sorted by license name.

Severity classification for pip-audit findings is done by querying the
[OSV API](https://osv.dev/) for each advisory's `database_specific.severity`
field (the GitHub Advisory Database label). pip-audit itself does not emit
CVSS or GHSA severity. The script is offline-tolerant: if OSV is
unreachable, findings classify as `UNKNOWN` and the script falls back to
treating them as non-failing (they remain visible in the printed report).

## Responding to a High/Critical finding

The triage runbook when the weekly audit goes red, or when a local
`bash scripts/audit-deps.sh` exits non-zero:

1. **Confirm** — re-run `bash scripts/audit-deps.sh` locally on `main` to
   reproduce. Cache poisoning is rare but possible; a clean re-run rules it
   out.
2. **Classify** —
    * If pip-audit, note the advisory ID (GHSA or CVE) and the affected
      package + installed version.
    * If npm audit, note the GHSA URL printed for each `via:` leaf advisory.
3. **Check for an upstream fix** —
    * Python: `uv pip show <pkg>` and look at the `Fix Versions` column
      from pip-audit. If a patched version exists, run
      `uv add '<pkg>>=<fixed>'` (or update the existing pin in
      `pyproject.toml`) and `uv lock`.
    * Node: read the `fixAvailable` field of `npm audit --json`. If true,
      `npm audit fix` (or a manual bump of the direct dependency that owns
      the transitive). If false, jump to step 5.
4. **Patch, test, commit** —
    * Branch off `main`.
    * Update the version, re-run `uv sync --locked --dev` / `npm ci`.
    * Run the full local check: `uv run ruff check . && uv run ruff format
      --check . && uv run mypy --strict . && uv run pytest`.
    * Re-run `bash scripts/audit-deps.sh` to confirm the finding has
      cleared.
    * Open a PR. The standard CI pipeline (`.github/workflows/ci.yml`) is
      the gate for merging.
5. **No fix available** — if upstream has not released a patched version:
    * Decide whether the advisory is exploitable in our context (read the
      advisory description; pay attention to the attack vector — network,
      local, build-time only).
    * If genuinely not exploitable, add the advisory ID to the
      `IGNORE_PIP_VULNS` or `IGNORE_NPM_GHSAS` array at the top of
      `scripts/audit-deps.sh` AND add a row to the "Known exceptions"
      section below with the justification + revisit date.
    * If exploitable and no fix is coming, the only options are
      replacing the dependency or accepting risk explicitly via a
      documented exception. Do not silently ignore.
6. **Rollback plan** — if the bump breaks something downstream and a fix
   is not immediately obvious, revert the version bump (`git revert
   <commit>` and `uv lock` / `npm ci` to restore the previous lock) and
   re-open the issue with the failure mode. The previous (vulnerable)
   pinned version stays in place until a safer fix is identified — this is
   acceptable for short windows because the project is personal-use only
   and the audit failure remains visible.

## Known exceptions

These advisories are currently ignored by `scripts/audit-deps.sh`. Each
entry must include the advisory ID, the affected package, why it cannot be
fixed today, why it is acceptable risk in this project, and a revisit date.

### Node (`IGNORE_NPM_GHSAS`)

| GHSA ID                | Package / chain                                                  | Rationale                                                                                                                                                                                                                                                                                                                                                                  | Revisit  |
|------------------------|------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| GHSA-34x7-hfp2-rc4v    | node-tar (via duckdb-async → duckdb → node-gyp → make-fetch-happen → cacache → tar) | Hardlink path-traversal during tar extraction. `npm audit` reports `fixAvailable: false`; the vulnerable tar is bundled inside `node-gyp`'s nested `node_modules`, which only runs at install/build time, never at runtime in this project. We do not extract attacker-controlled tarballs.                                                                                | 2026-Q3 |
| GHSA-8qq5-rm4j-mr97    | node-tar (same chain as above)                                   | Symlink poisoning via insufficient path sanitization during extraction. Same mitigation: build-time only, no attacker-controlled tarballs.                                                                                                                                                                                                                                  | 2026-Q3 |
| GHSA-83g3-92jg-28cx    | node-tar (same chain)                                            | Arbitrary file read/write via hardlink target escape through symlink chains. Same mitigation rationale.                                                                                                                                                                                                                                                                     | 2026-Q3 |
| GHSA-qffp-2rhf-9h96    | node-tar (same chain)                                            | Hardlink path-traversal via drive-relative linkpath. Same mitigation rationale.                                                                                                                                                                                                                                                                                              | 2026-Q3 |
| GHSA-9ppj-qmqm-q256    | node-tar (same chain)                                            | Symlink path-traversal via drive-relative linkpath. Same mitigation rationale.                                                                                                                                                                                                                                                                                              | 2026-Q3 |
| GHSA-r6q2-hw4h-h46w    | node-tar (same chain)                                            | Race condition in path reservations via Unicode ligature collisions on macOS APFS. Same mitigation rationale.                                                                                                                                                                                                                                                               | 2026-Q3 |

The cluster of `node-tar` advisories all reach us via the same
`duckdb-async → duckdb` chain. When `duckdb` ships a release that bundles
an updated `node-gyp` (or eliminates `node-gyp` altogether — `node-gyp`
itself is being deprecated in favour of the npm-internal build), every
entry above should clear in a single bump. Revisit quarterly.

### Python (`IGNORE_PIP_VULNS`)

None currently. The previously-flagged Moderate finding (`CVE-2026-45409`
in `idna 3.13`) was cleared on 2026-05-23 by `uv lock --upgrade-package
idna`, which bumped the transitive dep to `3.16` (past the `3.15` fix).
`bash scripts/audit-deps.sh` now reports zero Python vulnerabilities at
any severity.

## License compatibility policy

This project is personal-use, not redistributed. The license policy below
is therefore advisory rather than legally load-bearing — its purpose is to
avoid silently pulling in copyleft code that would complicate any future
decision to publish.

### Approved licenses (no review required)

A transitive dependency under any of these licenses is automatically
acceptable:

* **MIT** / **MIT License**
* **BSD-2-Clause** / **BSD-3-Clause** / **BSD License**
* **Apache-2.0** / **Apache Software License**
* **ISC**
* **PSF-2.0** / **Python Software Foundation License**
* **MPL 2.0** (Mozilla Public License 2.0) — file-level copyleft only,
  acceptable for use without modification.
* **Unlicense** / **CC0 1.0 Universal**
* Dual-licensed packages where at least one component is on this list
  (e.g. "Apache Software License; MIT License") are acceptable.

### Reviewed licenses (case-by-case)

These licenses require maintainer review before adding a dependency that
ships under them:

* **LGPL** (any version) — dynamic linking allowed; static linking
  triggers copyleft. Acceptable for Python (always dynamic) but record
  the rationale.
* **EPL** / **CDDL** — weak copyleft, mostly fine but record.
* **UNKNOWN** — a `pip-licenses` output of `UNKNOWN` means the upstream
  package omitted classifier metadata. Investigate the actual license
  before relying on it. (The repo's own `mortgage-ops` package will show
  as `UNKNOWN` in the inventory; this is expected and not a finding.)

### Blocked licenses (do not add)

* **GPL** (any version) — strong copyleft, contaminates the surrounding
  code if ever redistributed.
* **AGPL** — even network use triggers copyleft.
* **Proprietary** / **Commercial-only** licenses without an explicit grant
  for this project.
* Any license without a clear OSI-approved equivalent that has not been
  individually reviewed.

### Review process for a new license

1. The PR author runs `bash scripts/audit-deps.sh` and notes any new
   license appearing in section 3 (pip-licenses output).
2. If the new license is in "Approved" above, no action needed.
3. If it is in "Reviewed" or unfamiliar, the PR description must include
   a one-paragraph rationale: what the dependency does, why no
   permissively-licensed alternative was used, and any compliance
   implications.
4. If it is in "Blocked", the PR is rejected; find an alternative or
   open an issue to negotiate an exception.

Note: license enforcement is **informational only** — `audit-deps.sh`
does **not** fail the build on license changes. Drift detection is a
human review responsibility at PR time.
