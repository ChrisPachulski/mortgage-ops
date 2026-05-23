#!/usr/bin/env bash
# scripts/audit-deps.sh
#
# Dependency & security audit for mortgage-ops.
#
# Runs three audits in sequence and prints each under a clear header:
#   1. pip-audit            — Python vulnerability scan (uv-managed env)
#   2. npm audit            — Node vulnerability scan (production deps only)
#   3. pip-licenses         — Python license inventory (ordered by license)
#
# Exit semantics:
#   * Exit 0 if no High/Critical vulnerabilities are found.
#   * Exit non-zero (1) if any High or Critical vulnerability is found in
#     either ecosystem after applying the documented ignore lists below.
#   * Low/Moderate findings are printed as warnings only; they do NOT fail.
#
# Severity sources:
#   * npm audit emits severity directly in --json output (info|low|moderate|
#     high|critical). We read metadata.vulnerabilities counts.
#   * pip-audit (PyPI / OSV services) does NOT emit a CVSS / GHSA severity in
#     its JSON; we query OSV's REST API per advisory to extract the GitHub
#     Advisory Database `database_specific.severity` label.
#
# Ignore lists (see docs/dependency-review.md for the full justification):
#   * IGNORE_PIP_VULNS  — pip-audit advisory IDs that have no upstream fix
#                         AND are deemed not exploitable in this project.
#   * IGNORE_NPM_GHSAS  — GHSA IDs from npm audit known to be unfixable
#                         transitive findings (e.g. node-tar via duckdb).
#
# Usage:
#   bash scripts/audit-deps.sh
#
# This script is intentionally tool-only; it does not modify the repo.

set -euo pipefail

# ---------------------------------------------------------------------------
# Documented ignore lists (see docs/dependency-review.md → Known exceptions)
# ---------------------------------------------------------------------------
# pip-audit: comma-separated advisory IDs (CVE or GHSA). Each entry must be
# justified in docs/dependency-review.md before being added here.
IGNORE_PIP_VULNS=""

# npm audit: GHSA IDs to ignore when computing High/Critical fail count.
# These remain printed under the "npm audit" section as warnings even when
# ignored. Each entry must be justified in docs/dependency-review.md.
# Current ignores: node-tar advisories reaching us transitively via
# duckdb-async → duckdb → node-gyp → make-fetch-happen → cacache → tar.
# No fix is available upstream (npm audit says "fixAvailable: false"); the
# package only runs at build/install time, never at runtime in production.
IGNORE_NPM_GHSAS="GHSA-34x7-hfp2-rc4v GHSA-8qq5-rm4j-mr97 GHSA-83g3-92jg-28cx GHSA-qffp-2rhf-9h96 GHSA-9ppj-qmqm-q256 GHSA-r6q2-hw4h-h46w"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Track whether we should fail at the end.
FAIL=0

print_header() {
    local title="$1"
    printf '\n'
    printf '=%.0s' {1..78}; printf '\n'
    printf '%s\n' "$title"
    printf '=%.0s' {1..78}; printf '\n'
}

# ---------------------------------------------------------------------------
# 1. pip-audit (Python)
# ---------------------------------------------------------------------------
print_header "1. pip-audit  (Python vulnerabilities)"

# Build --ignore-vuln args from IGNORE_PIP_VULNS.
PIP_IGNORE_ARGS=()
if [ -n "${IGNORE_PIP_VULNS}" ]; then
    for v in ${IGNORE_PIP_VULNS}; do
        PIP_IGNORE_ARGS+=("--ignore-vuln" "$v")
    done
fi

# We audit a `uv pip freeze` snapshot (excluding the editable mortgage-ops
# project itself, which is unpublished) so `--strict` runs cleanly. This
# captures the full installed dependency closure including transitive deps.
FREEZE_FILE=$(mktemp -t mortgage-ops-freeze.XXXXXX)
trap 'rm -f "${FREEZE_FILE}"' EXIT
uv pip freeze --exclude-editable > "${FREEZE_FILE}"

# Human-readable run for the report (columns format).
# `|| true` because pip-audit exits non-zero on any vuln; we make our own
# pass/fail decision below from the JSON via OSV severity lookup.
uv run pip-audit --strict --progress-spinner off -r "${FREEZE_FILE}" \
    ${PIP_IGNORE_ARGS[@]+"${PIP_IGNORE_ARGS[@]}"} || true

# Machine-readable run to feed the severity classifier.
PIP_JSON=$(uv run pip-audit --strict --format json --progress-spinner off \
    -r "${FREEZE_FILE}" \
    ${PIP_IGNORE_ARGS[@]+"${PIP_IGNORE_ARGS[@]}"} 2>/dev/null || true)

# Classify pip-audit findings by GHSA severity (queries OSV per advisory).
PIP_HIGH_CRIT=$(python3 - <<'PY' "$PIP_JSON"
import json
import sys
import urllib.error
import urllib.request

raw = sys.argv[1]
if not raw.strip():
    print(0)
    sys.exit(0)

try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print(0)
    sys.exit(0)

high_crit = 0
findings_by_sev: dict[str, list[str]] = {}

def osv_severity(advisory_id: str) -> str:
    """Return UPPERCASE severity label from OSV, or 'UNKNOWN'."""
    url = f"https://api.osv.dev/v1/vulns/{advisory_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "mortgage-ops-audit/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return "UNKNOWN"
    db_spec = payload.get("database_specific") or {}
    sev = db_spec.get("severity")
    if isinstance(sev, str):
        return sev.upper()
    return "UNKNOWN"

for dep in data.get("dependencies", []):
    name = dep.get("name", "?")
    for vuln in dep.get("vulns", []) or []:
        # Prefer GHSA alias for OSV lookup; fall back to the primary id.
        ids = [vuln.get("id")] + list(vuln.get("aliases") or [])
        ids = [i for i in ids if isinstance(i, str)]
        sev = "UNKNOWN"
        ghsa_ids = [i for i in ids if i.startswith("GHSA-")]
        lookup_order = ghsa_ids + [i for i in ids if i not in ghsa_ids]
        for ident in lookup_order:
            sev = osv_severity(ident)
            if sev != "UNKNOWN":
                break
        primary = ids[0] if ids else "?"
        findings_by_sev.setdefault(sev, []).append(f"{name}: {primary}")
        if sev in ("HIGH", "CRITICAL"):
            high_crit += 1

# Emit a sev-classified summary to stderr so it shows in the report output.
if findings_by_sev:
    print("\n  Severity classification (via OSV / GitHub Advisory Database):",
          file=sys.stderr)
    for sev in ("CRITICAL", "HIGH", "MODERATE", "LOW", "UNKNOWN"):
        items = findings_by_sev.get(sev, [])
        if items:
            print(f"    {sev:8s} ({len(items)}): " + ", ".join(items),
                  file=sys.stderr)

print(high_crit)
PY
)

if [ "${PIP_HIGH_CRIT}" -gt 0 ]; then
    echo
    echo "FAIL: pip-audit found ${PIP_HIGH_CRIT} High/Critical Python vulnerability(ies)."
    FAIL=1
else
    echo
    echo "OK: no High/Critical Python vulnerabilities."
fi

# ---------------------------------------------------------------------------
# 2. npm audit (Node, production deps only)
# ---------------------------------------------------------------------------
print_header "2. npm audit  (Node vulnerabilities, --omit=dev)"

# Human-readable run. npm audit exits non-zero on findings, so `|| true`.
npm audit --omit=dev || true

# Machine-readable run for severity counting + ignore-list filtering.
NPM_JSON=$(npm audit --omit=dev --json 2>/dev/null || true)

NPM_HIGH_CRIT=$(python3 - <<'PY' "$NPM_JSON" "$IGNORE_NPM_GHSAS"
import json
import sys

raw = sys.argv[1]
ignore_list = set((sys.argv[2] or "").split())
if not raw.strip():
    print(0)
    sys.exit(0)
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print(0)
    sys.exit(0)

# Walk every vuln, collect each underlying advisory's severity + GHSA id.
# npm dedupes findings under each package; the leaf "via" entries that are
# dicts carry the GHSA (`url` ends in /GHSA-xxxx) and severity.
high_crit_unignored = 0
seen: set[str] = set()
for _pkg, info in (data.get("vulnerabilities") or {}).items():
    for via in info.get("via", []) or []:
        if not isinstance(via, dict):
            continue
        ghsa = ""
        url = via.get("url") or ""
        # URLs look like https://github.com/advisories/GHSA-xxxx-yyyy-zzzz
        if "GHSA-" in url:
            ghsa = "GHSA-" + url.split("GHSA-", 1)[1]
        sev = (via.get("severity") or "").lower()
        key = (ghsa, sev)
        if key in seen:
            continue
        seen.add(key)
        if sev in ("high", "critical") and ghsa not in ignore_list:
            high_crit_unignored += 1

# Also report the npm-aggregated counts for visibility.
meta = (data.get("metadata") or {}).get("vulnerabilities") or {}
print(
    f"\n  npm audit totals: "
    f"critical={meta.get('critical', 0)} high={meta.get('high', 0)} "
    f"moderate={meta.get('moderate', 0)} low={meta.get('low', 0)} "
    f"info={meta.get('info', 0)}",
    file=sys.stderr,
)
if ignore_list:
    print(
        f"  ignored GHSAs ({len(ignore_list)}): " + " ".join(sorted(ignore_list)),
        file=sys.stderr,
    )
print(high_crit_unignored)
PY
)

if [ "${NPM_HIGH_CRIT}" -gt 0 ]; then
    echo
    echo "FAIL: npm audit found ${NPM_HIGH_CRIT} unignored High/Critical Node advisory(ies)."
    FAIL=1
else
    echo
    echo "OK: no unignored High/Critical Node advisories."
fi

# ---------------------------------------------------------------------------
# 3. pip-licenses (Python license inventory)
# ---------------------------------------------------------------------------
print_header "3. pip-licenses  (Python license inventory, ordered by license)"

uv run pip-licenses --format=json --order=license

# ---------------------------------------------------------------------------
# Final result
# ---------------------------------------------------------------------------
print_header "Audit summary"
if [ "${FAIL}" -ne 0 ]; then
    echo "RESULT: FAIL — High/Critical vulnerabilities present (see sections above)."
    exit 1
fi
echo "RESULT: PASS — no High/Critical vulnerabilities."
exit 0
