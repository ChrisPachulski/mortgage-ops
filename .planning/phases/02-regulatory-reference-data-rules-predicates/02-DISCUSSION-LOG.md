# Phase 2: Regulatory Reference Data & Rules Predicates - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-26
**Phase:** 02-regulatory-reference-data-rules-predicates
**Areas discussed:** Scope of remaining 5 predicates, County subset, Types location, Pub 936 grace period, Staleness override

---

## Scope of remaining 5 predicates

### Q1 — Phase 2 scope size

| Option | Description | Selected |
|--------|-------------|----------|
| Ship all 11 this phase | Add plans 02-05/06 (and possibly 07) to cover Fannie LLPA + Freddie + PMI + ATR/QM + Reg Z. Phase 4 affordability gets full predicate library day-one. | ✓ |
| Ship 8, defer Fannie/Freddie matrices | Add plan 02-05 covering PMI + ATR/QM + Reg Z only. Defer RUL-02 + RUL-03 to a Phase 2.5 or fold into Phase 4. | |
| Ship 9, defer only Fannie LLPA | Add plan 02-05 with PMI + Freddie + ATR/QM + Reg Z. Only Fannie LLPA (largest, most volatile) deferred. | |

**User's choice:** Ship all 11 this phase
**Notes:** No deferral pressure. Phase 4 affordability gets full library day-one with no surprises.

### Q2 — Plan packaging

| Option | Description | Selected |
|--------|-------------|----------|
| 3 more plans: 02-05, 02-06, 02-07 | 02-05 PMI+Fannie+Freddie / 02-06 ATR/QM+Reg Z / 02-07 citation-coverage hardening + final schema audit. Total = 7 plans. | ✓ |
| 2 more plans: 02-05, 02-06 | 02-05 PMI+Fannie+Freddie / 02-06 ATR/QM+Reg Z + final meta-test pass. Total = 6 plans. | |
| Granular: 02-05 PMI, 02-06 Fannie, 02-07 Freddie, 02-08 ATR/QM+RegZ | One predicate per plan for matrix-heavy ones. Total = 8 plans. | |

**User's choice:** 3 more plans (02-05, 02-06, 02-07)
**Notes:** Plan 02-07 is non-mergeable — final audit gate protects Phase 4+ from inheriting predicate-library rot. Locked in CONTEXT.md as D-03.

### Q3 — Fannie LLPA matrix scope

| Option | Description | Selected |
|--------|-------------|----------|
| Primary-residence purchase + rate-and-term refi only | ~50 cells each = ~100 total. Investment/second-home/cash-out → NotImplementedError. RESEARCH §Open-Q3 recommendation. | |
| Primary-residence purchase only | Just FICO × LTV grid for owner-occupied purchase (~50 cells). Refi adjustments + investment + second-home all NotImplementedError. | |
| Full matrix | All occupancy/purpose/unit-count branches. Hundreds of cells. Most robust but largest extraction lift. | ✓ |

**User's choice:** Full matrix
**Notes:** Accept the YAML maintenance burden. Annual refresh = meaningful YAML edit. Plan 02-05 is heavier — planner has discretion to split internally as sub-tasks but NOT into 02-05a/b without re-discussion.

### Q4 — REF-IDs for Fannie/Freddie matrix YAMLs

| Option | Description | Selected |
|--------|-------------|----------|
| Implementation detail under RUL-02/03 | Don't change REQUIREMENTS.md count (stays 22 / 116 total). YAMLs added silently under RUL-02/03 with documentation in plan rationale. RESEARCH §Open-Q1 recommendation. | ✓ |
| Add REF-10 Fannie + REF-11 Freddie | Promote to first-class requirements. Phase 2 count → 24, total v1 → 118. Cleaner audit trail but mid-flight REQUIREMENTS.md edit. | |
| Add as sub-numbered (REF-02b style) | Less disruptive renumbering; signals matrix-companion to existing predicates. | |

**User's choice:** Implementation detail under RUL-02/03
**Notes:** Accepted that requirements coverage gate (plan-checker) will need to verify RUL-02/03 plans implicitly include the YAMLs. Document in plan rationale.

---

## County subset for REF-01 / REF-02 / REF-06

| Option | Description | Selected |
|--------|-------------|----------|
| Top 100 high-cost + all WA counties | Top 100 by metro pop (~95% volume) + every WA county. USDA: WA + top 50 nationally. Unlisted high-cost county → MissingCountyDataError. | ✓ |
| All ~232 high-cost counties + comprehensive USDA | Full FHFA + HUD per-county XLSX. Bigger YAMLs, no error surprises. Linear annual refresh burden. | |
| Only WA + neighboring states (OR, ID, CA) | Pacific Northwest + California focus. Smallest YAMLs. Future relocation = annual refresh + extension. | |

**User's choice:** Top 100 high-cost + all WA counties
**Notes:** Locked as D-06. Loud failure on unlisted high-cost county (MissingCountyDataError) so user knows to extend rather than silently treating as baseline.

---

## Types location

| Option | Description | Selected |
|--------|-------------|----------|
| `lib/rules/types.py` (new file) | Keeps Phase 1's `lib/models.py` untouched. Phase 4+ imports from both. RESEARCH §Open-Q4 recommendation. | ✓ |
| Extend `lib/models.py` | Single source of truth. Touches frozen-surface file. | |

**User's choice:** lib/rules/types.py (new file)
**Notes:** Locked as D-07. Phase 1 frozen surface preserved. Promotion to lib/models.py deferred until types prove broadly useful.

---

## IRS Pub 936 grace period

| Option | Description | Selected |
|--------|-------------|----------|
| Confirm: per-debt boolean flags | RUL-11 input takes binding_contract_signed_before_2017_12_15 + binding_contract_closed_before_2018_04_01 booleans. Both True → grandfathered $1M cap. | ✓ |
| Override: single origination_date heuristic | Use loan origination_date alone; before 2017-12-15 → grandfathered cap. Less precise but simpler API. | |

**User's choice:** Confirm per-debt boolean flags
**Notes:** Locked as D-09. Confirms what existing 02-04 plan inferred as D-PHASE2-Q5. Caller sources truth-values from settlement statements.

---

## Staleness override

| Option | Description | Selected |
|--------|-------------|----------|
| No override — let it warn | Warning is correct: YAMLs are >12mo old even if regulator hasn't republished. Yearly nudge to verify. Aligns with "fail loud" discipline. | ✓ |
| Add per-file `staleness_acknowledged_until` field | Optional override suppresses warning for genuinely-unchanged regulator data. Adds maintenance step. | |

**User's choice:** No override — let it warn
**Notes:** Locked as D-12. Override field deferred to v2 if noise becomes a real annoyance.

---

## Claude's Discretion

Areas where planner / executor have flexibility:

- Loader implementation (`lru_cache(maxsize=None)`, fresh-dict-per-call discipline, `cache_clear()` for test isolation)
- YAML schema validation approach (Pydantic v2 + per-loader validation; no Cerberus / jsonschema)
- `yaml.safe_load` discipline (never `yaml.load`)
- Test fixture format (JSON files in `tests/fixtures/rules/` with `citation` + `source_url` + `comment` fields)
- Predicate file structure (module docstring with citation + source URL + effective date + pattern reference)
- Wave 3 sequencing (02-05/06 may parallelize within Wave 3 if no shared file modifications)
- Plan 02-05 internal sub-task splitting (PMI, Fannie, Freddie as separate sub-tasks within one plan)

## Deferred Ideas

- `staleness_acknowledged_until` YAML field — v2 if noisy
- Pre-2023-03-20 FHA MIP rules — RUL-04 raises NotImplementedError for old endorsement dates
- Pub 936 points-deductibility (§3) — out of v1
- HPA pre-1999 loans — out of scope (HPA is 1999+)
- Freddie LPA black-box AUS replication — out of v1 (per PROJECT.md)
- Refi treatment of conventional PMI — Phase 6's job, not RUL-05
- Annual refresh automation (Playwright scrape) — v2 (AUTO-01)
- County geocoding — caller-responsibility
