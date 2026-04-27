---
phase: 02-regulatory-reference-data-rules-predicates
plan: 07
subsystem: testing
tags: [audit-gate, mutation-testing, meta-tests, citation-coverage, schema-audit, smoke-test, phase-2-close]

# Dependency graph
requires:
  - phase: 02-regulatory-reference-data-rules-predicates
    provides: 11 predicates (lib/rules/*.py) + 10 reference YAMLs (data/reference/*.yml) + citation-coverage meta-test + schema meta-test (shipped 02-01..02-06)
provides:
  - Mutation harness proving the citation-coverage and schema meta-tests catch their target regression classes (no longer vacuously green)
  - Pinned YAML count audit (10) and predicate count audit (11) — silent additions/omissions now fail loud
  - Cross-predicate import smoke + happy-path call validation for reg_z and conventional_pmi
  - Phase 2 audit-gate ratification — Phase 4+ inherits a non-broken predicate library
affects: [phase-04-affordability, phase-06-refi-npv, phase-07-apr, phase-08-stress, future-annual-regulatory-refresh]

# Tech tracking
tech-stack:
  added: []  # zero new dependencies — audit-only plan
  patterns:
    - "Mutation-test harness via subprocess + tmp_path-cloned repo (proves meta-tests have teeth)"
    - "Filesystem-introspecting count audit with paired count + stems set assertions (catches rename-pairs)"
    - "Cross-module import smoke (catches ImportError cascades that per-predicate test files miss)"

key-files:
  created:
    - tests/test_rules/test_citation_coverage_mutations.py
    - tests/test_reference/test_yaml_count_audit.py
    - tests/test_rules/test_phase2_smoke.py
  modified: []  # zero existing files modified

key-decisions:
  - "02-07: Mutation-test isolation via subprocess against shutil.copytree clone (NEVER monkeypatch the meta-test in-process — defeats isolation). Reusable for any future meta-test mutation harness (Phase 7 APR Newton-Raphson tolerance check, Phase 12 eval harness regression detection)."
  - "02-07: Anchored vs substring line-strip mutation. YAML key mutations (`source:` / `effective:` at line start) MUST use anchored regex matching (`^\\s*key:`) to avoid stripping `source_url:`-style false positives. Predicate docstring mutations use substring match because Citation:/Source URL:/Effective: may appear multiple times and stripping all is desired. Reusable for any future YAML-field mutation."
  - "02-07: Paired count + stems assertions for filesystem audits. Two test functions (count match + stems set match) catch the rename-pair edge case where two YAMLs are renamed simultaneously and the count happens to balance. Single count assertion would silently pass. Reusable for any future filesystem-introspecting count audit (Phase 9 DuckDB schema files, Phase 12 eval harness fixtures)."
  - "02-07: Import-only smoke for the 9 YAML-backed predicates; happy-path call only for the 2 pure-Python predicates (reg_z + conventional_pmi). Calling all 11 with regulator-pinned inputs would duplicate per-predicate test files (which already exist) and add multi-arg call shapes (atr_qm + fannie_eligibility) that have no minimal happy-path. Reusable for any future cross-module smoke."

patterns-established:
  - "Mutation harness for meta-tests: subprocess.run(['uv', 'run', 'pytest', '-x'], cwd=clone, check=False) with assert returncode != 0 — never imports the meta-test in-process. Auditable, proves teeth."
  - "Filesystem audit pairing: count assertion + frozenset stems assertion (catches rename-pairs that preserve count). Both assertions live in the same audit file with explicit EXPECTED_* constants."
  - "Cross-module smoke: import every expected module, surface ALL failures in one assertion (failures: list[tuple[str, str]] accumulator) — not a per-module pytest parametrize. Catches ImportError cascades fast."

requirements-completed: [RUL-12, RUL-13, REF-09]  # Final-pass audit confirming requirements 02-01 marked complete

# Metrics
duration: 4min
completed: 2026-04-27
---

# Phase 02 Plan 07: Citation-Coverage Audit Gate Summary

**Mutation harness, YAML count audit, and cross-predicate smoke ratifying that Phase 2's 11-predicate library + 10 reference YAMLs ship with meta-tests that actually have teeth.**

## Performance

- **Duration:** ~4 min (sequential, single executor)
- **Started:** 2026-04-27T04:33:23Z
- **Completed:** 2026-04-27T04:37:15Z
- **Tasks:** 5 (4 auto + 1 checkpoint:human-verify auto-approved per yolo mode)
- **Files created:** 3
- **Files modified:** 0 (audit-only plan; zero production code changes)
- **Tests added:** +14 net (7 mutation harness + 2 YAML count audit + 5 Phase 2 smoke)
- **Total tests after:** 224 (up from 210)

## Audit Verdict

**PASS.** All four full-stack gates exit 0 with the complete Phase 2 deliverable set loaded.

| Gate | Result |
|------|--------|
| `uv run pytest --tb=short` | 224 passed, 4 expected StaleReferenceWarnings (D-12 accepted) |
| `uv run mypy --strict .` | Success: no issues found in 47 source files |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 47 files already formatted |

## On-Disk Counts at Audit Time

| Pinned count | Expected | Actual | Status |
|--------------|----------|--------|--------|
| `lib/rules/*.py` predicates (excl. `__init__.py`, `_loader.py`, `types.py`) | 11 | 11 | match |
| `data/reference/*.yml` files | 10 | 10 | match |
| Citation-coverage parametrized cases (11 predicates × 2 tests) | 22 | 22 | match |
| Schema parametrized cases (one per YAML) | 10 | 10 | match |
| Mutation harness tests | 7 | 7 | match |
| YAML count audit tests | 2 | 2 | match |
| Phase 2 smoke tests | 5 | 5 | match |

## Mutation Harness Results

All six regression classes were caught (plus one unmutated baseline confirming clone integrity):

| Test | Mutation | Result |
|------|----------|--------|
| `test_strip_citation_line_makes_meta_test_fail` | Strip `Citation:` lines from `lib/rules/conventional_pmi.py` (in clone) | CAUGHT — meta-test exited non-zero with `Citation:` in output |
| `test_strip_source_url_line_makes_meta_test_fail` | Strip `Source URL:` lines | CAUGHT — meta-test exited non-zero with `Source URL:` in output |
| `test_strip_effective_line_makes_meta_test_fail` | Strip `Effective:` lines | CAUGHT — meta-test exited non-zero with `Effective:` in output |
| `test_delete_fixture_makes_meta_test_fail` | Delete all `tests/fixtures/rules/conventional_pmi_*.json` | CAUGHT — fixture meta-test exited non-zero with `conventional_pmi` in output |
| `test_strip_yaml_source_makes_schema_test_fail` | Strip anchored `source:` from `data/reference/conforming-limits-2026.yml` | CAUGHT — schema meta-test exited non-zero with `source` in output |
| `test_strip_yaml_effective_makes_schema_test_fail` | Strip anchored `effective:` from same YAML | CAUGHT — schema meta-test exited non-zero with `effective` in output |
| `test_meta_tests_pass_unmutated_baseline` | None — sanity check on clone | PASSED — both meta-tests green on unmutated clone |

**No mutations escaped.** No live-tree pollution: `git status --porcelain lib/ data/reference/ tests/fixtures/rules/ tests/test_rules/test_citation_coverage.py tests/test_reference/test_schema.py` returned 0 lines after the suite ran.

## Roster Verification

### Predicate Roster (11 — pinned in `EXPECTED_PREDICATE_MODULES`)

| Plan  | Module                              | Imports cleanly |
|-------|-------------------------------------|-----------------|
| 02-01 | `lib.rules.loan_type`               | yes |
| 02-02 | `lib.rules.fha_mip`                 | yes |
| 02-03 | `lib.rules.va_funding_fee`          | yes |
| 02-03 | `lib.rules.va_residual_income`      | yes |
| 02-04 | `lib.rules.usda`                    | yes |
| 02-04 | `lib.rules.irs_pub936`              | yes |
| 02-05 | `lib.rules.conventional_pmi`        | yes |
| 02-05 | `lib.rules.fannie_eligibility`      | yes |
| 02-05 | `lib.rules.freddie_eligibility`     | yes |
| 02-06 | `lib.rules.atr_qm`                  | yes |
| 02-06 | `lib.rules.reg_z`                   | yes |

### YAML Roster (10 — pinned in `EXPECTED_YAML_STEMS`)

| Plan  | Stem                          | Source                              |
|-------|-------------------------------|-------------------------------------|
| 02-01 | `conforming-limits-2026`      | REF-01                              |
| 02-02 | `fha-limits-2026`             | REF-02                              |
| 02-02 | `fha-mip-rates`               | REF-03                              |
| 02-03 | `va-funding-fees`             | REF-04                              |
| 02-03 | `va-residual-income`          | REF-05                              |
| 02-04 | `usda-income-limits`          | REF-06                              |
| 02-04 | `irs-pub936`                  | REF-07                              |
| 02-05 | `fannie-llpa-matrix`          | RUL-02 implementation-detail (D-05) |
| 02-05 | `freddie-eligibility-matrix`  | RUL-03 implementation-detail (D-05) |
| 02-06 | `atr-qm-thresholds`           | RUL-09 implementation-detail        |

### Happy-Path Smoke Calls

- `reg_z.within_apr_tolerance(disclosed=0.05, actual=0.0515, irregular=False)` → `False` (|diff|=0.0015 > 0.00125 regular tolerance per §1026.22(a)(2))
- `reg_z.within_apr_tolerance(disclosed=0.05, actual=0.0501, irregular=False)` → `True` (|diff|=0.0001 within tolerance)
- `conventional_pmi.status(loan, scheduled_balance=78, original_property_value=100)` at exactly LTV=0.78 → `"auto_terminated"` per HPA §4902(b)

## Task Commits

Each task was committed atomically:

1. **Task 1: Citation-coverage mutation harness** — `72684b4` (test)
2. **Task 2: YAML count audit pinning to 10** — `58762da` (test)
3. **Task 3: Phase 2 cross-predicate smoke pinning to 11** — `a526733` (test)
4. **Task 4: Full-stack gate (verification only — no commit)** — N/A
5. **Task 5: Human-verify checkpoint (auto-approved per `mode: yolo` config — no manual blockers; all automated criteria green)** — N/A

**Plan metadata:** appended after this SUMMARY commit.

## Files Created/Modified

- `tests/test_rules/test_citation_coverage_mutations.py` (new, 229 lines) — 7 tests proving the citation-coverage + schema meta-tests catch their target regression classes via subprocess + tmp_path clone
- `tests/test_reference/test_yaml_count_audit.py` (new, 82 lines) — 2 tests pinning YAML count at 10 and stems set
- `tests/test_rules/test_phase2_smoke.py` (new, 161 lines) — 5 tests covering predicate count, filesystem stems, every-import-clean, and 2 happy-path predicate calls

## Decisions Made

(All decisions extracted to `key-decisions` frontmatter above; logged to STATE.md after this SUMMARY.)

1. **Mutation-test isolation via subprocess + shutil.copytree clone** — never monkeypatch the meta-test in-process. A successfully-mutated in-process test is indistinguishable from a buggy mutation harness. Reusable across the project.
2. **Anchored regex line-strip for YAML keys; substring strip for predicate docstring lines** — `source_url:` collisions ruled out for the YAML mutation; predicate docstring mutations want all lines stripped.
3. **Paired count + stems assertions** — single count assertion would silently miss simultaneous renames that preserve count.
4. **Import-only smoke for 9 predicates; happy-path calls for only `reg_z` + `conventional_pmi`** — the 2 pure-Python predicates have minimal call surfaces; the 9 YAML-backed predicates have multi-arg shapes already covered by per-predicate test files. Calling all 11 would duplicate work.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed inapplicable `# noqa: BLE001` directive in test_phase2_smoke.py**
- **Found during:** Task 3 (Phase 2 cross-predicate smoke)
- **Issue:** The plan spec at line 775 included `except Exception as exc:  # noqa: BLE001 — we want every failure listed`. Ruff config at `pyproject.toml:34-43` enables `["E", "F", "W", "I", "UP", "B", "SIM", "RUF", "TCH", "PT"]` but does NOT enable `BLE` rules. Ruff RUF100 fired with "Unused `noqa` directive (non-enabled: `BLE001`)".
- **Fix:** Replaced `# noqa: BLE001 — we want every failure listed` with a plain inline comment `# we want every failure listed in one assertion`. The bare `Exception` catch is intentional and accepted by the project's ruff config without a noqa.
- **Files modified:** `tests/test_rules/test_phase2_smoke.py`
- **Verification:** `uv run ruff check tests/test_rules/test_phase2_smoke.py` exits 0; pytest still passes 5/5
- **Committed in:** `a526733` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — Rule 1: ruff RUF100 inapplicable noqa)
**Impact on plan:** Trivial fix; semantics unchanged. The plan-author wrote the noqa speculatively assuming BLE rules were enabled; they aren't, and the bare Exception catch needs no suppression. No scope creep.

## Issues Encountered

None. The plan executed exactly as written modulo the single trivial ruff RUF100 deviation above.

## User Setup Required

None — audit-only plan. No external services, no environment variables, no dashboard configuration.

## Threat Surface Scan

No new security-relevant surface introduced. The mutation harness uses `subprocess.run([list, of, args], shell=False)` with static literal arguments (no user input), eliminating shell-injection surface (T-02-07-06 in plan threat register). The clone never escapes `tmp_path` (`shutil.copytree` with `dirs_exist_ok=False`). Live source tree pollution defended by acceptance criteria + post-task `git status` check.

## Threat Register Disposition Status

| Threat ID | Disposition | Status |
|-----------|-------------|--------|
| T-02-07-01 (Tampering: meta-test weakened) | mitigate | ENFORCED — 6 mutations × non-zero exit assertions |
| T-02-07-02 (Tampering: YAML loses required field) | mitigate | ENFORCED — schema mutations + count audit |
| T-02-07-03 (Information Disclosure: live tree pollution) | mitigate | ENFORCED — `shutil.ignore_patterns` + `cwd=clone` + post-suite git status = 0 |
| T-02-07-04 (Repudiation: green claim with no evidence) | mitigate | ENFORCED — Task 5 checkpoint surfaces commands + outputs in this SUMMARY |
| T-02-07-05 (DoS: clone too slow) | mitigate | ENFORCED — full mutation suite ~7s; `ignore_patterns` skips caches |
| T-02-07-06 (EoP: shell injection) | accept | ACCEPTED — `subprocess.run(list, shell=False)` static literals only |
| T-02-07-07 (Spoofing: predicate count drift) | mitigate | ENFORCED — symmetric stems comparison surfaces both missing AND unexpected |
| T-02-07-08 (Information Disclosure: stale warnings as errors) | accept | ACCEPTED — pytest config does not promote warnings; smoke does not use `pytest.warns(error=True)` |

## Task 5 Sign-Off Note

Per the spawn prompt's instruction "If a task explicitly asks for user confirmation per the plan, surface it as a checkpoint. Otherwise complete normally" combined with `mode: yolo` in `.planning/config.json` (auto-approve gates) and the fact that ALL automated criteria from the plan's `<how-to-verify>` block are green:

- Four-command full-stack gate: green (224 passed, mypy/ruff clean across 47 files)
- Predicate count: 11 (matches expected)
- YAML count: 10 (matches expected)
- Three audit-test files exist, each > 50 lines (229, 82, 161)
- 14 audit tests pass in isolation (7 mutation + 2 yaml count + 5 smoke)
- No live-tree pollution after mutation harness ran
- All audit tests programmatically verify the conditions a human would otherwise eyeball

The audit gate is ratified. Phase 2 is complete. Phase 4 (affordability) may now begin consuming `lib.rules.*` per the contracts in `02-CONTEXT.md` `<code_context>` lines 162–163. If anything subsequently surfaces that the automated suite missed, a follow-up plan will address it — but the dispositions in the threat register and the success criteria checklist are all green.

## Phase 2 Closure

Plan 02-07 is the final plan in Phase 2. After this commit:

- **Plans complete:** 7/7 (was 6/7)
- **Phase 2 status:** Complete
- **Predicate library status:** RATIFIED — every predicate has citation header + ≥1 fixture, every reference YAML has `source:` + `effective:`, mutation tests prove the audit catches regressions
- **Total Phase 2 wall time:** ~75 min (35 + 7 + 12 + 5 + 10 + 5 + ~4)
- **Velocity baseline:** ~6.7 min/plan averaged across the phase; ~3 min/plan in steady state (post-foundation)

## Next Phase Readiness

Phase 4 (Affordability) consumers are now safe to import:
- `lib.rules.loan_type.classify`
- `lib.rules.fha_mip.compute_mip`
- `lib.rules.va_residual_income.evaluate` (stable `binding_rule_citation` per D-11; AFFD-07 sentinel preserved)
- `lib.rules.fannie_eligibility.compute_llpa`
- `lib.rules.usda.evaluate`
- `lib.rules.atr_qm.general_qm_passes`

Phase 6 (Refi NPV) consumers:
- `lib.rules.conventional_pmi.status` (HPA at refi: caller resets `original_property_value`)

Phase 7 (Estimated APR) consumers:
- `lib.rules.reg_z.within_apr_tolerance` (Decimal abs-diff comparison; `is_irregular_transaction` is caller-classified)

No blockers. No deferred follow-ups specific to 02-07. The deferred items inherited from earlier plans (D-12 staleness override field, pre-2023 FHA grandfathering, Pub 936 points deductibility, HPA pre-1999 grandfathering, refi treatment, full LPA replication, county geocoding, annual refresh automation) all remain v2.

## Self-Check: PASSED

**Created files (3):**
- `tests/test_rules/test_citation_coverage_mutations.py` — FOUND
- `tests/test_reference/test_yaml_count_audit.py` — FOUND
- `tests/test_rules/test_phase2_smoke.py` — FOUND

**Commits (3 task + 1 metadata):**
- `72684b4` (Task 1) — FOUND
- `58762da` (Task 2) — FOUND
- `a526733` (Task 3) — FOUND
- Metadata commit — pending after this SUMMARY write

---
*Phase: 02-regulatory-reference-data-rules-predicates*
*Completed: 2026-04-27*
