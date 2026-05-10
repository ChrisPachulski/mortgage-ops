---
phase: 10
plan: 04
subsystem: claude-skill
tags:
  - phase-10
  - claude-skill
  - references
  - skll-08
  - skll-09
  - progressive-disclosure
dependency_graph:
  requires:
    - 10-00
    - 10-02
  provides:
    - SKLL-08
    - SKLL-09
  affects:
    - .claude/skills/mortgage-ops/references/
    - .claude/skills/mortgage-ops/assets/
tech_stack:
  added: []
  patterns:
    - byte-equal-mirror (cp not symlink) for cross-folder reference duplication; drift-protection via Wave 5 byte-equality tests
    - progressive-disclosure references (loaded on demand from SKILL.md topic→reference table; not eagerly loaded)
key_files:
  created:
    - .claude/skills/mortgage-ops/references/arm-mechanics.md
    - .claude/skills/mortgage-ops/references/refi-npv.md
    - .claude/skills/mortgage-ops/references/apr-reg-z.md
    - .claude/skills/mortgage-ops/references/amortization-formulas.md
    - .claude/skills/mortgage-ops/references/affordability-rules.md
    - .claude/skills/mortgage-ops/references/gse-limits.md
    - .claude/skills/mortgage-ops/references/mip-pmi.md
    - .claude/skills/mortgage-ops/references/spreadsheet-conventions.md
    - .claude/skills/mortgage-ops/references/tax-deductibility.md
    - .claude/skills/mortgage-ops/assets/.gitkeep
  modified: []
decisions:
  - "Byte-lift pattern extends from arm-mechanics.md (Phase 5) to refi-npv.md (Phase 6) and apr-reg-z.md (Phase 7) — three drift-protected mirrors total, all using `cp -p` (not symlinks), all with Wave 5 byte-equality tests pending."
  - "tax-deductibility.md cites `qualified_loan_limit(...)` (NOT `qualified_loan_limit_worksheet(...)`); function name verified against lib/rules/irs_pub936.py line 60 per Round-2 codex LOW 12."
  - "All 9 reference files end with `Last reviewed: 2026-05-08` (today's date) so future maintainers know when content was last cross-checked."
  - "Marker-stub strategy obsolete — Phase 6/7 are COMPLETE per STATE.md, so refi-npv.md and apr-reg-z.md ship as full-content lifts (~630 / ~523 lines), NOT 25-line forward-link stubs."
metrics:
  duration_seconds: 391
  duration_minutes: 6.5
  tasks_completed: 5
  files_created: 10
  completed_date: 2026-05-08
---

# Phase 10 Plan 04: References Summary

Shipped 9 progressive-disclosure references inside `.claude/skills/mortgage-ops/references/` (3 byte-equal mirrors of project-root counterparts, 5 authored fresh from Phase 1-5 + Phase 2 source-of-truth artifacts, 1 hybrid Phase 2 + Phase 6 cross-link), plus the `assets/.gitkeep` placeholder. SKLL-08 closes fully — no marker stubs remain. Pre-existing 551 test baseline preserved.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Byte-lift arm-mechanics.md (Phase 5 source) | bd4a76d | `.claude/skills/mortgage-ops/references/arm-mechanics.md` |
| 2 | Byte-lift refi-npv.md (Phase 6) + apr-reg-z.md (Phase 7) | d2554ed | `.claude/skills/mortgage-ops/references/{refi-npv,apr-reg-z}.md` |
| 3 | Author 5 full-content references | 97e50e9 | `amortization-formulas.md`, `affordability-rules.md`, `gse-limits.md`, `mip-pmi.md`, `spreadsheet-conventions.md` |
| 4 | Author tax-deductibility.md (Phase 2 + Phase 6 cross-link) | 845356f | `.claude/skills/mortgage-ops/references/tax-deductibility.md` |
| 5 | Create assets/.gitkeep + final verification | a3ce125 | `.claude/skills/mortgage-ops/assets/.gitkeep` |

## Reference Files Shipped (9 total)

| Filename | Lines | ~cl100k tokens | Source phase | Lift strategy |
|----------|-------|----------------|--------------|---------------|
| arm-mechanics.md | 196 | ~1,632 | Phase 5 (lib/arm.py) | byte-equal mirror (cp from `<repo>/references/`) |
| refi-npv.md | 630 | ~5,063 | Phase 6 (lib/refinance.py) | byte-equal mirror (cp from `<repo>/references/`) |
| apr-reg-z.md | 523 | ~3,775 | Phase 7 (lib/apr.py) | byte-equal mirror (cp from `<repo>/references/`) |
| amortization-formulas.md | 87 | ~873 | Phase 3 + FND-09 oracles | authored fresh |
| affordability-rules.md | 88 | ~803 | Phase 4 lib/affordability.py + Phase 2 predicates | authored fresh |
| gse-limits.md | 72 | ~824 | REF-01 + REF-02 YAMLs | authored fresh |
| mip-pmi.md | 75 | ~997 | REF-03 + RUL-04 + RUL-05 | authored fresh |
| spreadsheet-conventions.md | 75 | ~890 | numpy-financial bugs #130 + #131 + Excel sign | authored fresh |
| tax-deductibility.md | 76 | ~858 | Phase 2 (REF-07 + RUL-11) + Phase 6 cross-link | authored fresh hybrid |

Token estimates approximated via `words × 1.3`; final ratification in Wave 5 token-budget test if added.

## Drift-Protection Verification

All three byte-equal mirrors confirmed byte-identical against project-root counterparts at commit time:

```
$ diff references/arm-mechanics.md  .claude/skills/mortgage-ops/references/arm-mechanics.md
(empty — exits 0)
$ diff references/refi-npv.md       .claude/skills/mortgage-ops/references/refi-npv.md
(empty — exits 0)
$ diff references/apr-reg-z.md      .claude/skills/mortgage-ops/references/apr-reg-z.md
(empty — exits 0)
```

Wave 5 will ship three pytest tests asserting the same:
- `test_arm_mechanics_skill_mirror_in_sync`
- `test_refi_npv_skill_mirror_in_sync`
- `test_apr_reg_z_skill_mirror_in_sync`

Each runs `cmp` (or `filecmp.cmp(..., shallow=False)`) on the pair. Project-root files remain authoritative for `lib/*.py` docstring citations (`lib/arm.py`, `lib/refinance.py`, `lib/apr.py`); skill-folder copies keep the skill bundle self-contained when copied to another machine.

## Cross-Link Audit (data-flow forward-check)

Mode files (Wave 3) and SKILL.md (Wave 2) reference these references by exact filename. Verified:

| From | To | Verified |
|------|----|---------:|
| SKILL.md (line 125) topic→reference table | references/amortization-formulas.md | ✓ exact name match |
| SKILL.md (line 126) | references/apr-reg-z.md | ✓ |
| SKILL.md (line 127) | references/arm-mechanics.md | ✓ |
| SKILL.md (line 128) | references/refi-npv.md | ✓ |
| SKILL.md (line 129) | references/affordability-rules.md | ✓ |
| SKILL.md (line 130) | references/gse-limits.md | ✓ |
| SKILL.md (line 131) | references/mip-pmi.md | ✓ |
| SKILL.md (line 132) | references/tax-deductibility.md | ✓ |
| SKILL.md (line 133) | references/spreadsheet-conventions.md | ✓ |
| modes/_shared.md (line 66) | references/spreadsheet-conventions.md | ✓ |

All 9 SKILL.md cross-references resolve to files that now exist; no broken links.

## Acceptance Criteria — All Met

- [x] All 5 tasks executed in order
- [x] 9 reference files exist under `.claude/skills/mortgage-ops/references/` with the EXACT filenames specified by ROADMAP SC-5 / SKILL.md topic→reference table
- [x] arm-mechanics.md byte-equals project-root copy (`diff` exits 0; not a symlink)
- [x] refi-npv.md byte-equals project-root copy (`diff` exits 0; 630 lines ≥ 500 floor; no "Forward-Link Stub" / "load-when-Phase-X-lands" substrings)
- [x] apr-reg-z.md byte-equals project-root copy (`diff` exits 0; 523 lines ≥ 400 floor; no marker-stub substrings)
- [x] amortization-formulas.md ≥ 60 lines (87 actual), contains "$2,528.27" oracle value
- [x] affordability-rules.md ≥ 60 lines (88 actual), references reverse-affordability + npf.pv
- [x] gse-limits.md ≥ 40 lines (72 actual), references YAML paths
- [x] mip-pmi.md ≥ 40 lines (75 actual), mentions UFMIP + annual MIP + HPA
- [x] spreadsheet-conventions.md ≥ 30 lines (75 actual), mentions numpy-financial bugs
- [x] tax-deductibility.md ≥ 40 lines (76 actual), contains "$750,000" + "after-tax" + "Phase 6" + `qualified_loan_limit(` and DOES NOT contain `qualified_loan_limit_worksheet`
- [x] Each authored file ends with "Last reviewed: 2026-05-08"
- [x] No User Layer PII in any file (placeholders only)
- [x] `.claude/skills/mortgage-ops/assets/.gitkeep` exists, zero bytes
- [x] Pre-existing test suite green (551 passed, 4 skipped, 16 xfailed, baseline preserved)

## Deviations from Plan

None — plan executed exactly as written. The Round-2 plan revisions (HIGH-7 byte-lift expansion to 3 files, LOW-12 `qualified_loan_limit` function-name correction, today's-date "Last reviewed" stamps) are all baked into the plan we executed and were respected throughout.

## Authentication Gates

None encountered.

## Threat Model Compliance

Per `<threat_model>` in 10-04 PLAN.md:
- T-10-22 (arm-mechanics drift) — mitigated by byte-equal cp; Wave 5 ships test
- T-10-23 (refi-npv drift) — mitigated by byte-equal cp; Wave 5 ships test
- T-10-43 (apr-reg-z drift) — mitigated by byte-equal cp; Wave 5 ships test
- T-10-50 (cross-folder mirror drift, all three) — mitigated; Wave 5 byte-compare tests pending
- T-10-24 (regulatory misstatement) — every authored file cites lib/rules/* + data/reference/* sources
- T-10-25 (PII leak) — placeholders only; no household.yml values copied
- T-10-26 (oversized reference DoS) — all 9 files ≤ ~5,063 cl100k tokens (well under 10,000 ceiling); only one ref loaded per query per progressive-disclosure rule

## Threat Flags

None — Wave 4 introduces no new network endpoints, auth paths, file-access patterns, or schema changes at trust boundaries. All file additions are documentation-only inside `.claude/skills/mortgage-ops/references/` and a zero-byte placeholder.

## Known Stubs

None — all 9 references ship full content. The "marker-stub" strategy from the pre-Round-2 plan version was retired because Phase 6/7 are COMPLETE per STATE.md. Wave 4 SKLL-08 closure is full, not partial-with-stubs.

## TDD Gate Compliance

Plan type is `execute` (not `tdd`); RED/GREEN/REFACTOR gate sequence does not apply. Wave 5 will flip the existing xfail stubs (`tests/test_skill.py::test_references_exist` etc.) once the per-reference assertions land.

## Self-Check: PASSED

Verified files exist:
- FOUND: .claude/skills/mortgage-ops/references/arm-mechanics.md
- FOUND: .claude/skills/mortgage-ops/references/refi-npv.md
- FOUND: .claude/skills/mortgage-ops/references/apr-reg-z.md
- FOUND: .claude/skills/mortgage-ops/references/amortization-formulas.md
- FOUND: .claude/skills/mortgage-ops/references/affordability-rules.md
- FOUND: .claude/skills/mortgage-ops/references/gse-limits.md
- FOUND: .claude/skills/mortgage-ops/references/mip-pmi.md
- FOUND: .claude/skills/mortgage-ops/references/spreadsheet-conventions.md
- FOUND: .claude/skills/mortgage-ops/references/tax-deductibility.md
- FOUND: .claude/skills/mortgage-ops/assets/.gitkeep

Verified commits exist:
- FOUND: bd4a76d (Task 1)
- FOUND: d2554ed (Task 2)
- FOUND: 97e50e9 (Task 3)
- FOUND: 845356f (Task 4)
- FOUND: a3ce125 (Task 5)
