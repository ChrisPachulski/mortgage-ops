---
phase: 09-duckdb-orchestration
plan: 05
subsystem: reference-layer

tags:
  - phase-09
  - duckdb-orchestration
  - known-loans
  - reference-layer
  - product-catalog
  - pers-07
  - roadmap-sc-5

# Dependency graph
requires:
  - phase: 09-duckdb-orchestration
    plan: 00
    provides: "tests/test_orchestration/test_known_loans_smoke.py xfail stub awaiting flip (REPO_ROOT-anchored CATALOG_PATH already in place)"
provides:
  - "data/known-loans.yml — Reference Layer product catalog committed to git; 7 representative mortgage products (conv-30yr-fixed, conv-15yr-fixed, arm-5-1, arm-7-1, fha-30yr, va-30yr, jumbo-30yr-fixed); top-level source: + effective: 2026-04-24"
  - "9-key per-entry schema (id, label, loan_type, principal, apr, term_months, frequency, origination_date, citation_url) with loan_type drawn from lib.models.Loan Literal options"
  - "Decimal-string discipline preserved end-to-end: principal + apr are quoted strings (str via yaml.safe_load); apr at 6-decimal precision"
  - "PERS-07 closed at the test layer (test_known_loans_catalog_complete now PASSES; xfail removed)"
  - "ROADMAP SC-5 satisfied (catalog completeness asserted by executable test, not hand-eyeball)"
affects:
  - "10-claude-skill (Phase 10) — `evaluate` mode now has a stable product-ID set to route off; catalog round-trips into lib/models.py:Loan via the loan_type discriminator"
  - "12-fred-eval (Phase 12) — eval-harness regression set can seed prompts from catalog entries; product IDs are pinned by the smoke test against accidental rename"
  - "09-06 concurrency (Wave 6) — independent (no DB or lockfile interactions in this plan); does not change the concurrency surface"
  - "09-07 references doc (Wave 7) — references doc will describe the catalog's role in the Reference Layer"

# Tech tracking
tech-stack:
  added: []  # No new runtime libraries; uses PyYAML (Phase 1) + js-yaml verified at sanity-check level (Wave 2 dep)
  patterns:
    - "Reference Layer YAML convention: top-level `source:` (URL) + `effective:` (ISO date) + body array — matches Phase 2 reference-yaml shape (data/reference/conforming-limits-2026.yml etc.)"
    - "Decimal-string discipline through YAML: money + rate fields quoted as strings (`\"400000.00\"`, `\"0.068100\"`) so yaml.safe_load returns str, not float; preserves precision losslessly through round-trip into Decimal"
    - "Field-name round-trip into Pydantic model: catalog discriminator is `loan_type:` (matches lib/models.py:45 Loan.loan_type attribute), not a generic `type:`; smoke test asserts membership in the Loan Literal option set (D-05-02 revision)"
    - "Test schema gate: REQUIRED_IDS + REQUIRED_PER_ENTRY_KEYS typed as frozenset[str] at module level — mypy-strict-friendly, immutable, and document the contract once at the top of the file"

key-files:
  created:
    - "data/known-loans.yml — 79 lines; 7 product entries; tracked by git (NOT in .gitignore); SHA-stable header comment block + source/effective + products array"
    - ".planning/phases/09-duckdb-orchestration/09-05-SUMMARY.md (this file)"
  modified:
    - "tests/test_orchestration/test_known_loans_smoke.py — 28 -> 111 lines (+83 net): removed @pytest.mark.xfail decorator + Wave 0 stub body; added full assertion flow (catalog exists, root is mapping, source/effective present, products is list, REQUIRED_IDS subset, per-entry 9-key schema, principal+apr are str, loan_type is Loan-Literal member); REQUIRED_IDS + REQUIRED_PER_ENTRY_KEYS typed as frozenset[str]; pytest + TYPE_CHECKING imports removed"

key-decisions:
  - "D-05-01 LOCKED: data/known-loans.yml lives directly under data/, NOT data/reference/ and NOT inside data/mortgage-ops.duckdb — DATA_CONTRACT.md line 67 places it at data/known-loans.yml; the catalog is product metadata, not regulatory data; the duckdb file is gitignored Data Layer (would prevent the catalog from being a committed artifact)"
  - "D-05-02 LOCKED (revision 2026-05-04): Per-entry 9-key schema is {id, label, loan_type, principal, apr, term_months, frequency, origination_date, citation_url} — superseded the original D-05-02 (`type:`) because PATTERNS.md + lib/models.py:45 specify Loan.loan_type as the model attribute; using `type:` would silently break Phase 10 round-trip into the Pydantic model; smoke test now asserts loan_type ∈ {fixed, arm, fha, va, usda, jumbo}"
  - "D-05-03 LOCKED: principal + apr MUST be quoted strings in YAML — CLAUDE.md money discipline is non-negotiable; YAML auto-coerces unquoted `400000.00` to a Python float (lossy at scale); `\"400000.00\"` round-trips losslessly to Decimal; smoke test asserts isinstance(p['principal'], str) + isinstance(p['apr'], str) per entry"
  - "D-05-04 LOCKED: APR precision is 6 decimal places (e.g., \"0.068100\") — matches the RESEARCH sample verbatim; 6 decimals preserves basis-point precision (0.0001 = 1bp); FRED MORTGAGE30US is published to 2 decimals (6.81%) but stored at 6 (\"0.068100\") for round-trip safety with internal Decimal precision"
  - "D-05-05 LOCKED: Smoke test asserts SET MEMBERSHIP (`REQUIRED_IDS <= ids`), not equality — PERS-07 says \"AT LEAST\" the 7 listed products; future phases may add more (e.g., USDA, 20yr fixed) without breaking the contract; equality would force every catalog edit to also edit the test"
  - "D-05-06 LOCKED: Reference Layer convention keys (source:, effective:) are TOP LEVEL, not nested per product — matches Phase 2 reference YAMLs; the staleness check (Phase 2 REF-08) reads top-level effective:; per-entry citation lives in citation_url (different from catalog-wide source:), giving a correct two-level provenance model"
  - "D-05-07 LOCKED: Smoke test does NOT load known-loans.yml via Node — Pitfall 4 (Cross-Process DuckDB Access) does not apply because YAML files have no lock; both Python yaml.safe_load and Node js-yaml can read concurrently with no contention; smoke test's job is shape verification, Node consumption is exercised when downstream phases call js-yaml (validated as a manual sanity check during execution: js-yaml correctly preserves principal as quoted string)"

patterns-established:
  - "Reference Layer YAML shape: header comments + top-level source/effective + body array — directly extensible to additional Reference Layer artifacts (e.g., future data/known-properties.yml, data/known-employers.yml) without inventing a new shape"
  - "Decimal-string-through-YAML idiom: money/rate fields quoted to preserve string type through yaml.safe_load; consumers parse with Decimal() constructor; this is the third reuse of the pattern (Phase 2 reference YAMLs, Phase 1 Pydantic Money/Rate, now Phase 9 catalog) and is the canonical money-on-disk shape for this project"
  - "Pydantic-attribute-driven YAML field naming: catalog field names match the Pydantic model attribute names (loan_type, not type) so the YAML round-trips into the model with no key remapping; eliminates a class of silent bugs where YAML loads but Pydantic .model_validate raises"
  - "Test-side typed module-level constants: REQUIRED_IDS + REQUIRED_PER_ENTRY_KEYS as frozenset[str] documents the contract at the top of the file, satisfies mypy --strict, and prevents the test body from accumulating magic-set literals"

requirements-completed:
  - PERS-07  # data/known-loans.yml ≥ 7 entries loadable + Reference Layer convention pinned by smoke test

# Metrics
duration: 6min
completed: 2026-05-04
---

# Phase 09 Plan 05: Known-Loans Catalog Summary

**data/known-loans.yml shipped as the Reference Layer product catalog (79 lines: header + source/effective + 7 product entries with 9-key schema each); test_known_loans_catalog_complete xfail flipped to PASSED; pass count 534 -> 535; xfail count 4 -> 3; PERS-07 + ROADMAP SC-5 closed.**

## Performance

- **Duration:** ~6 min (start 2026-05-04T00:00:00Z approximate; end immediately after final commit)
- **Tasks:** 2 (Task 1 catalog write + commit, Task 2 test flip + commit)
- **Files modified:** 2 (data/known-loans.yml created, tests/test_orchestration/test_known_loans_smoke.py replaced)
- **Lines added:** +79 known-loans.yml (new file); +99 / -15 test_known_loans_smoke.py (xfail stub replaced with full assertion flow)

## Catalog Anatomy

**data/known-loans.yml — 79 lines, 7 product entries**

```
source: https://www.freddiemac.com/pmms          # Reference Layer convention (top-level)
effective: 2026-04-24                            # Reference Layer convention (top-level; staleness input)

products:
  - id: conv-30yr-fixed     loan_type: fixed   principal: "400000.00"  apr: "0.068100"  term: 360  (FRED MORTGAGE30US)
  - id: conv-15yr-fixed     loan_type: fixed   principal: "400000.00"  apr: "0.060500"  term: 180  (FRED MORTGAGE15US)
  - id: arm-5-1             loan_type: arm     principal: "400000.00"  apr: "0.062500"  term: 360  (CFPB ARM)
  - id: arm-7-1             loan_type: arm     principal: "400000.00"  apr: "0.064000"  term: 360  (CFPB ARM)
  - id: fha-30yr            loan_type: fha     principal: "400000.00"  apr: "0.066500"  term: 360  (HUD 203(b))
  - id: va-30yr             loan_type: va      principal: "400000.00"  apr: "0.063500"  term: 360  (VA HOMELOANS)
  - id: jumbo-30yr-fixed    loan_type: jumbo   principal: "1000000.00" apr: "0.069500"  term: 360  (FHFA 2026 limits)
```

**loan_type breakdown:**

| loan_type | Count | Entries |
|-----------|-------|---------|
| fixed | 2 | conv-30yr-fixed, conv-15yr-fixed |
| arm | 2 | arm-5-1, arm-7-1 |
| fha | 1 | fha-30yr |
| va | 1 | va-30yr |
| jumbo | 1 | jumbo-30yr-fixed |
| usda | 0 | (Loan Literal includes usda; no USDA product in v1 — D-05-05 subset semantics allow Phase 10+ to add) |
| **TOTAL** | **7** | |

All five values used (fixed/arm/fha/va/jumbo) are members of the lib.models.Loan.loan_type Literal option set.

## Reference Layer Placement Confirmation

| Check | Result |
|-------|--------|
| `data/known-loans.yml` exists | Yes (79 lines) |
| Path is directly under `data/` (not `data/reference/`) | Yes (D-05-01) |
| `git check-ignore data/known-loans.yml` | exits 1 (NOT gitignored — committed Reference Layer) |
| Top-level `source:` key | 1 occurrence (`grep -c '^source:' data/known-loans.yml` = 1) |
| Top-level `effective:` key | 1 occurrence (`grep -c '^effective:' data/known-loans.yml` = 1) |
| `effective:` value | 2026-04-24 (FRED PMMS week) |

## Decimal-String Discipline Confirmation

| Field | Pattern | Match Count | Required |
|-------|---------|-------------|----------|
| principal | `^\s+principal: "[0-9]+\.[0-9]{2}"` | 7 | ≥ 7 |
| apr | `^\s+apr: "0\.[0-9]{6}"` | 7 | ≥ 7 |

Sanity-check via js-yaml: first product principal returned as JS string `"400000.00"` (not number `400000`); confirms quoted-string preservation across the Python <-> Node parser boundary.

## Field-Name Round-Trip Gate

| Check | Result | Required |
|-------|--------|----------|
| `loan_type:` with valid Literal value | 7 entries match `^\s+loan_type: (fixed\|arm\|fha\|va\|usda\|jumbo)$` | ≥ 7 |
| Legacy `type:` key (D-05-02 revision negative gate) | 0 entries match `^\s+type: ` | == 0 |
| Required IDs present (PERS-07 set) | 7/7: conv-30yr-fixed, conv-15yr-fixed, arm-5-1, arm-7-1, fha-30yr, va-30yr, jumbo-30yr-fixed | 7/7 |

Both the positive gate (`loan_type:` ≥ 7) and the negative gate (`type:` == 0) are satisfied. The catalog is ready to round-trip into lib/models.py:Loan in Phase 10 with no key remapping.

## Test Counts

- **Pre-Wave-5 baseline (Plan 09-04 final):** 534 passed + 4 skipped + 4 xfailed
- **Post-Wave-5 (Plan 09-05 final):** **535 passed + 4 skipped + 3 xfailed** (+1 net pass; -1 net xfail; zero regression)
- **Plan target:** 535 passed + 3 xfailed — **HIT EXACTLY**

The 3 remaining system-wide xfails:
1. `test_oracle_cross_validation_5_1` (Phase 5 ARM oracle deferral — not Phase 9)
2. `test_concurrent_writes_serialize` (Wave 6)
3. `test_stale_lockfile_reclaimed_after_60s` (Wave 6)

`test_known_loans_catalog_complete` is no longer in the xfail list — it now PASSES.

## Wave-Flip Status

| Stub | File | Pre-Wave-5 | Post-Wave-5 |
|------|------|------------|-------------|
| `test_init_db_idempotent` | test_db_lifecycle.py | PASSED | PASSED |
| `test_insert_loan_round_trip` | test_db_lifecycle.py | PASSED | PASSED |
| `test_insert_scenario_round_trip` | test_db_lifecycle.py | PASSED | PASSED |
| `test_insert_report_round_trip` | test_db_lifecycle.py | PASSED | PASSED |
| `test_decimal_string_round_trip_preserves_cents` | test_db_lifecycle.py | PASSED | PASSED |
| `test_render_markdown_byte_identical` | test_render_markdown.py | PASSED | PASSED |
| `test_known_loans_catalog_complete` | test_known_loans_smoke.py | XFAIL | **PASSED ✓ (this wave)** |
| `test_concurrent_writes_serialize` | test_db_lifecycle.py | XFAIL | XFAIL (Wave 6) |
| `test_stale_lockfile_reclaimed_after_60s` | test_lockfile.py | XFAIL | XFAIL (Wave 6) |

Wave 5 flips exactly 1 xfail (test_known_loans_catalog_complete), per the plan's success criteria.

## Smoke Test (Manual)

```bash
$ uv run python -c "import yaml; d = yaml.safe_load(open('data/known-loans.yml')); print(len(d['products']), 'products'); print(sorted(p['id'] for p in d['products']))"
7 products
['arm-5-1', 'arm-7-1', 'conv-15yr-fixed', 'conv-30yr-fixed', 'fha-30yr', 'jumbo-30yr-fixed', 'va-30yr']

$ node -e "const yaml=require('js-yaml');const fs=require('fs');const d=yaml.load(fs.readFileSync('data/known-loans.yml','utf-8'));console.log('products via js-yaml:',d.products.length);console.log('first principal:',JSON.stringify(d.products[0].principal));"
products via js-yaml: 7
first principal: "400000.00"

$ git check-ignore data/known-loans.yml; echo "exit=$?"
exit=1                                                         # NOT ignored — Reference Layer committed

$ uv run pytest tests/test_orchestration/test_known_loans_smoke.py -v
tests/test_orchestration/test_known_loans_smoke.py::test_known_loans_catalog_complete PASSED  [100%]
============================== 1 passed in 0.02s ===============================

$ uv run pytest -q
535 passed, 4 skipped, 3 xfailed, 3 warnings in 15.81s
```

Both Python (yaml.safe_load) and Node (js-yaml) load the catalog cleanly. The smoke test passes in isolation; the full suite shows the expected +1 pass / -1 xfail delta with zero regression. The catalog is NOT gitignored (exit=1 from git check-ignore), confirming Reference Layer placement.

## Task Commits

Each task was committed atomically (no Co-Authored-By or AI attribution per global Git Attribution rule):

1. **Task 1: feat(09-05): commit data/known-loans.yml product catalog (PERS-07)** — `0a8a511`
2. **Task 2: test(09-05): flip test_known_loans_catalog_complete xfail to passing** — `15630e7`

## Files Modified

- `data/known-loans.yml` — NEW, 79 lines. Reference Layer product catalog. Contents:
  - Header comment block (5 lines): catalog purpose, "representative not live", FRED PMMS rate week 2026-04-24, ARM/FHA/VA/jumbo from agency rate-sheet samples
  - `source: https://www.freddiemac.com/pmms` (top-level)
  - `effective: 2026-04-24` (top-level)
  - `products:` array with 7 entries; each entry has all 9 required keys (id, label, loan_type, principal, apr, term_months, frequency, origination_date, citation_url)
  - All money values (principal) and rate values (apr) quoted as strings; apr at 6-decimal precision
  - Citations: FRED MORTGAGE30US/MORTGAGE15US, CFPB ARM page, HUD 203(b), VA HOMELOANS, FHFA 2026 conforming limits

- `tests/test_orchestration/test_known_loans_smoke.py` — 28 -> 111 lines (+83 net). Changes:
  - `@pytest.mark.xfail(strict=True, reason="Wave 0 stub - Plan 09-05 ships data/known-loans.yml")` decorator REMOVED
  - `pytest` and `TYPE_CHECKING` imports REMOVED (no longer needed)
  - `import yaml` PROMOTED to top-level
  - `pytest.fail("Wave 0 stub")` body REPLACED with full assertion flow:
    - Asserts `CATALOG_PATH.exists()` with descriptive message
    - Loads catalog via `yaml.safe_load(CATALOG_PATH.read_text())`; asserts root is dict
    - Asserts top-level `source:` and `effective:` keys (Reference Layer convention; DATA_CONTRACT.md line 69)
    - Asserts `products` key present + value is list
    - Asserts `REQUIRED_IDS - ids` is empty (D-05-05: subset semantics; PERS-07 closure)
    - Per-entry loop:
      - Asserts `REQUIRED_PER_ENTRY_KEYS - entry_keys` is empty (9-key schema enforced)
      - Asserts `isinstance(p["principal"], str)` (D-05-03 Decimal discipline)
      - Asserts `isinstance(p["apr"], str)` (D-05-03 Decimal discipline)
      - Asserts `p["loan_type"] in {"fixed","arm","fha","va","usda","jumbo"}` (D-05-02 revision: round-trip with lib.models.Loan.loan_type Literal)
  - REQUIRED_IDS + REQUIRED_PER_ENTRY_KEYS typed as `frozenset[str]` at module level (mypy --strict-friendly)
  - REPO_ROOT + CATALOG_PATH typed as `Path`; CATALOG_PATH = REPO_ROOT / "data" / "known-loans.yml"
  - Module + function docstrings updated to reflect Wave 5 deliverable (file shipped, contract pinned by executable test)

## Decisions Made

All seven decisions are LOCKED at the plan level (D-05-01..D-05-07) — the executor honored them verbatim. No new plan-level decisions emerged during execution. D-05-02 was already in revised form (loan_type:, not type:) at the start of Wave 5 per iter-2 plan-check; the executor applied the revised schema verbatim.

- **D-05-01 LOCKED — `data/known-loans.yml` (NOT `data/reference/known-loans.yml` and NOT inside `data/mortgage-ops.duckdb`):** DATA_CONTRACT.md line 67 explicitly enumerates `data/known-loans.yml` (no `reference/` subdir prefix); the catalog is product metadata, not regulatory data; the duckdb file is gitignored Data Layer (would prevent the catalog from being a committed artifact). Verified at `git check-ignore` level (exit 1).
- **D-05-02 LOCKED (revision 2026-05-04) — Per-entry 9-key schema with `loan_type:` (not `type:`):** PATTERNS.md line ~366 + lib/models.py:45 specify Loan.loan_type as the Pydantic model attribute name; using `type:` here would silently break Phase 10 round-trip into the Loan model; smoke test asserts loan_type ∈ {fixed, arm, fha, va, usda, jumbo}. Negative gate (`grep -cE '^\s+type: '` == 0) and positive gate (`grep -cE '^\s+loan_type: (fixed|arm|fha|va|usda|jumbo)$'` == 7) both green.
- **D-05-03 LOCKED — Money + rate fields quoted strings:** CLAUDE.md money discipline non-negotiable; YAML auto-coerces unquoted `400000.00` to a Python float (lossy at scale); `"400000.00"` round-trips losslessly to Decimal. Smoke test asserts isinstance(p['principal'], str) + isinstance(p['apr'], str) per entry. Verified via Python (yaml.safe_load returns str) and Node (js-yaml returns string `"400000.00"`).
- **D-05-04 LOCKED — APR precision 6 decimal places:** matches RESEARCH sample verbatim; 6 decimals preserves basis-point precision (0.0001 = 1bp). All 7 APRs match `^\s+apr: "0\.[0-9]{6}"`.
- **D-05-05 LOCKED — Smoke test asserts SET MEMBERSHIP (subset), not equality:** PERS-07 says "AT LEAST" 7 products; future phases may add USDA, 20yr fixed without breaking the contract. Test uses `REQUIRED_IDS - ids` (subset operator equivalent), not `REQUIRED_IDS == ids`.
- **D-05-06 LOCKED — Reference Layer convention keys top-level:** matches Phase 2 reference YAMLs; staleness check (Phase 2 REF-08) reads top-level effective:; per-entry citation lives in citation_url. Verified: `grep -c '^source:'` = 1; `grep -c '^effective:'` = 1.
- **D-05-07 LOCKED — Smoke test does NOT load via Node:** Pitfall 4 (Cross-Process DuckDB Access) does not apply; YAML files have no lock; Python yaml.safe_load is the test-side reader. Node consumption was exercised as a manual sanity check during execution (js-yaml correctly preserved principal as quoted string), confirming the file is parser-portable.

## Deviations from Plan

None. The plan was executed exactly as written. Both tasks shipped exactly the code specified by Task 1 and Task 2 actions.

The only mechanical adjustment during execution was running `uv run ruff format` on the test file to satisfy `ruff format --check` (the action's reference implementation included some line widths that ruff's formatter wanted to collapse — line 81 `f"... missing required product IDs: {sorted(missing)}; have: {sorted(ids)}"` was collapsed onto a single line by the formatter, and line 89 `f"product {p.get('id', '<unknown>')} missing keys: {sorted(entry_missing)}"` was likewise collapsed). This is Rule-4 lint hygiene (allowed by the plan's deviation rules: "ruff format may collapse multi-line literals; apply minimal fix and document"). The semantics and test pass status are unchanged.

No Rule-1 (bug), Rule-2 (missing critical functionality), or Rule-4 (architectural) deviations occurred.

## Issues Encountered

None — execution was clean.

## Lint + Type Hygiene Status

| Check | Result |
|-------|--------|
| `uv run pytest -q` | **535 passed + 4 skipped + 3 xfailed** (was 534+4+4; +1 pass, -1 xfail; zero regression) |
| `uv run pytest tests/test_orchestration/test_known_loans_smoke.py -v` | 1 passed in 0.02s |
| `uv run mypy --strict tests/test_orchestration/test_known_loans_smoke.py` | Success: no issues found in 1 source file |
| `uv run ruff check tests/test_orchestration/test_known_loans_smoke.py` | All checks passed |
| `uv run ruff format --check tests/test_orchestration/test_known_loans_smoke.py` | 1 file already formatted |
| `git check-ignore data/known-loans.yml` | exit 1 (NOT ignored — Reference Layer committed) |
| Python yaml.safe_load round-trip | 7 products; principal returned as str `"400000.00"` |
| Node js-yaml round-trip | 7 products; principal returned as string `"400000.00"` (cross-parser portability confirmed) |

Pre-commit hooks (ruff legacy alias, ruff format, mypy, check-yaml, user-layer-block) ran on both task commits and passed.

## User Setup Required

None — Wave 5 is a single committed YAML file + a test flip. No environment variables, dashboard configuration, credential setup, or schema migrations needed. The catalog is purely additive and consumed by Phase 10+ on demand.

## Threat Model Coverage

The plan's threat_model section enumerates 5 STRIDE threats (T-09-22..T-09-26). Implementation status:

| Threat ID | Mitigation Implemented | Verified By |
|-----------|------------------------|-------------|
| T-09-22 (Tampering: per-entry key drops silently break Phase 10 routing) | Smoke test asserts `REQUIRED_PER_ENTRY_KEYS - entry_keys == set()` for every product (D-05-02) | test_known_loans_catalog_complete fails CI if any entry loses any of the 9 required keys |
| T-09-23 (Information Disclosure: Decimal precision lost via unquoted YAML float) | Quoted-string convention (D-05-03); smoke test asserts `isinstance(p["principal"], str)` and `isinstance(p["apr"], str)` per entry | All 7 entries pass the type assertion; cross-parser sanity check (Python + Node) confirms string preservation |
| T-09-24 (Repudiation: rate quoted from no-source) | citation_url required key (D-05-02); every entry carries a citation URL | Per-entry 9-key schema check guarantees citation_url presence |
| T-09-25 (Tampering: catalog gitignored by accident, never committed) | `git check-ignore data/known-loans.yml` exit 1 (NOT ignored) — verified pre-commit; gitignore inspection shows no `data/*.yml` rule that would catch the catalog | Confirmed during Task 1 acceptance gate (exit=1); committed at 0a8a511 |
| T-09-26 (Spoofing: catalog presents stale rates as live offers) | Header comment "representative product, not a live offer"; `effective: 2026-04-24` discloses provenance; v1 risk acceptance per RESEARCH A5 | Header comment present at lines 1-5 of data/known-loans.yml; effective date is the freshness contract |

All 5 threats covered. T-09-26 is `accept` disposition (per plan threat register), so the mitigation is provenance disclosure (header comment + effective: date), not technical enforcement.

## Self-Check: PASSED

Verified at SUMMARY-write time:

**Files exist:**
- `data/known-loans.yml` exists at 79 lines (`wc -l` confirmed during execution)
- `tests/test_orchestration/test_known_loans_smoke.py` modified (xfail removed; 111 lines after ruff format)

**Commits exist:**
- `0a8a511` (Task 1: feat(09-05) commit known-loans.yml) — `git log --oneline -3` shows it
- `15630e7` (Task 2: test(09-05) flip xfail) — `git log --oneline -3` shows it

**Catalog content:**
- `grep -c '^  - id:' data/known-loans.yml` returns 7
- `grep -c '^source:' data/known-loans.yml` returns 1
- `grep -c '^effective:' data/known-loans.yml` returns 1
- `grep -cE '^\s+principal: "[0-9]+\.[0-9]{2}"' data/known-loans.yml` returns 7
- `grep -cE '^\s+apr: "0\.[0-9]{6}"' data/known-loans.yml` returns 7
- `grep -cE '^\s+loan_type: (fixed|arm|fha|va|usda|jumbo)$' data/known-loans.yml` returns 7
- `grep -cE '^[[:space:]]+type: ' data/known-loans.yml` returns 0 (negative gate; D-05-02 revision)
- All 7 required IDs present (1 occurrence each)
- `git check-ignore data/known-loans.yml` exits 1 (NOT ignored)

**Test:**
- `test_known_loans_catalog_complete` PASSES — verified via `pytest tests/test_orchestration/test_known_loans_smoke.py -v` (1 passed in 0.02s)
- `grep -c "@pytest.mark.xfail" tests/test_orchestration/test_known_loans_smoke.py` returns 0
- `grep -c "Wave 0 stub" tests/test_orchestration/test_known_loans_smoke.py` returns 0
- Full pytest suite reports 535 passed + 4 skipped + 3 xfailed (verified)
- mypy --strict + ruff check + ruff format --check all clean (verified)

**Round-trip portability:**
- Python `yaml.safe_load` returns 7 products; principal as str `"400000.00"` (verified)
- Node `js-yaml` returns 7 products; principal as string `"400000.00"` (verified — sanity-checked during execution; D-05-07 confirms this is not a test-time gate but parser-portability is real)

## Next Phase Readiness

**Wave 6 (Plan 09-06 concurrency tests) unblocked** — independent of this wave; concurrency tests exercise the lockfile + db-write writers, which are already shipped in Waves 1-3 and unaffected by the YAML catalog. The 2 remaining Wave-6 xfails (test_concurrent_writes_serialize, test_stale_lockfile_reclaimed_after_60s) are the natural Wave 6 deliverables.

**Wave 7 (Plan 09-07 references doc)** — will document the Reference Layer product catalog as a peer of the regulatory-data YAMLs (data/reference/*.yml); the catalog file path, schema (9-key), source/effective convention, and downstream consumers (Phase 10 evaluate, Phase 12 eval-harness) are all stable now.

**Phase 10 + Phase 12 unblocked at the catalog layer** — both phases can route off the 7 product IDs starting Wave 5. The smoke test pins the contract: any rename, key drop, or loan_type Literal violation will fail CI before downstream phases ingest the catalog.

**Cumulative phase status (after Wave 5):**
- PERS-01 (DB schema bootstrap) closed by Wave 2
- PERS-02 (lockfile) closed by Wave 1
- PERS-03 (insert subcommands) closed by Wave 3
- PERS-05 (withLock-wrapped writes) closed at grep level by Wave 3 (concurrency end-to-end test in Wave 6)
- PERS-06 (byte-identical render-markdown) closed by Wave 4
- **PERS-07 (known-loans.yml ≥ 7 entries loadable via smoke test) closed by THIS wave (Wave 5)**
- PERS-04 (concurrency end-to-end) — pending Wave 6

6 of 7 PERS-XX requirements closed. The Reference Layer product catalog is now the canonical product list other phases route against. ROADMAP SC-5 ("data/known-loans.yml catalog: 30yr fixed, 15yr fixed, ARM 5/1, ARM 7/1, FHA 30yr, VA 30yr, jumbo") satisfied at the test layer.

---
*Phase: 09-duckdb-orchestration*
*Plan: 05 (Wave 5 — known-loans-catalog)*
*Completed: 2026-05-04*
